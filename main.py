import sys, getopt
import csv
import requests
import re
from bs4 import BeautifulSoup
import textract
import os
import urllib

GENERIC_EMAIL_REGEX = '([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]{0,3})'
ROOT_PDFS_PATH = 'pdfs/'
COMMON_FILE_EXTENSIONS = ['png', 'jpe', 'jpg', 'img']

def main(argv):

    inputfile = ''
    outputfile = ''
    try:
        opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
    except getopt.GetoptError:
        print('usage: main.py -i <inputfile> -o <outputfile>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('usage: main.py -i <inputfile> -o <outputfile>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-o", "--ofile"):
            outputfile = arg
    print('Input file is "', inputfile)
    print('Output file is "', outputfile)

    # Create pdfs directory to store any PDFs we need to download if it doesn't exist already
    if not os.path.isdir('pdfs'):
        os.mkdir('pdfs')

    # Download PDFs
    researchPaperData = getDataForProvidedTSV(inputfile)

    # Print our results
    print('#############################################')
    with open(outputfile, 'w', newline='') as out_file:
        tsv_writer = csv.writer(out_file, delimiter='\t')
        tsv_writer.writerow(['PaperID', 'Emails', 'Link'])
        for id, researchPaperDatum in researchPaperData.items():
            tsv_writer.writerow([id, researchPaperDatum['emails'], researchPaperDatum['finalURL']])
    print('Results written to results.tsv')


def getDataForProvidedTSV(inputTSVFileName):
    print('Downloading...')
    alreadyDownloadedPDFs = get_pdf_paths()
    researchPaperData = {}

    # Start building dict of all the associated PDFs for each research paper in the given tsv...
    with open(inputTSVFileName) as tsv:
        reader = csv.reader(tsv, delimiter="\t", quotechar='"')
        for row in reader:
            #column 2 is where the link is
            if row[2]:
                #print(row[2])
                # column 0 is the ID of the research paper
                researchPaperData[row[0]] = {
                    'initialURL': row[2],
                    'finalURL': row[2],
                    'downloadedPDFPath': '',
                    'emails': []
                }

    # Map research paper ID and the downloaded PDF paths
    for id,datum in researchPaperData.items():
        # if id == '6yinwbfh':
        print('--------------------------------------------')
        print('For research paper ID: ' + id)

        pdfFilePath = ROOT_PDFS_PATH + id + '.pdf'
        if pdfFilePath in alreadyDownloadedPDFs:
            print('PDF has already been downloaded! Parsing!')
            emails = parse_pdf(pdfFilePath)
            datum['emails'] = emails
            continue


        initialURL = datum['initialURL']
        print('InitialURL: ' + initialURL)

        finalURL = getMetaRefreshRedirectfinalURL(initialURL)
        if finalURL:
            datum['finalURL'] = finalURL
            print('finalURL:' + finalURL)

            # Make request to finalURL
            try:
                response = requests.get(finalURL)
            except Exception as e:
                print('Error sending request:')
                print(e)
            except ConnectionResetError as e:
                print('ConnectionResetError!')
                print(e)
            else:
                # If the response directly gave us a PDF, download it and associate the path to the research paper ID in our dict
                contentType, encoding = response.headers['content-type'].split(';')
                print(contentType)

                if contentType == 'application/pdf':
                    print('Response is a PDF!')
                    datum['downloadedPDFPath'] =  pdfFilePath
                    with open(pdfFilePath, 'wb') as f:
                        f.write(response.content)
                        f.close()
                    # Find the emails in the PDF we just downloaded
                    emails = parse_pdf(pdfFilePath)
                    datum['emails'] = emails

                if contentType == 'text/html':
                    print('Response is another webpage!')

                    # Try to extract email from webpage itself
                    datum['emails'] = scrapeEmailsFromWebpage(response.content, datum)

                    # Then try to extract email from any potential PDF links on the page
                    newSplitWebpageURL = urllib.parse.urlparse(response.url);
                    newWebpageBaseURL = newSplitWebpageURL.scheme + '://' + newSplitWebpageURL.netloc
                    print('New webpage base url: ' + newWebpageBaseURL)
                    pdfFilePath = scrapePDFDownloadButtonFromWebpageAndDownload(response.content, datum, pdfFilePath, newWebpageBaseURL)
                    if pdfFilePath:
                        emails = parse_pdf(pdfFilePath)
                        #combine emails from webpage and PDF
                        datum['emails'] = combineListsRemoveDuplicates(datum['emails'], emails)
                    else:
                        print('Could not find PDF to be downloaded from webpage')

                # Make list of emails unique after we've tried extracting from everywhere
                datum['emails'] = makeListUnique(datum['emails'])
                # Remove any results that matched the regex, but we can selectively remove due to knowing they aren't email addresses
                datum['emails'] = removeEdgeCases(datum['emails'])
        else:
            print('No final URL')
            datum['emails'] = []

    return researchPaperData

def scrapeEmailsFromWebpage(webpageContent, datum):
    soup = BeautifulSoup(webpageContent, 'lxml')
    soup = soup.prettify('latin-1')
    soupString = str(soup)
    emails = find_emails(soupString)
    return emails

def scrapePDFDownloadButtonFromWebpageAndDownload(webpageContent, datum, pdfFilePath, newWebpageBaseURL):
    soup = BeautifulSoup(webpageContent, 'lxml')
    linksOnPage = soup.find_all('a')
    potentialPDFLinks = []

    for link in linksOnPage:
        linkTitles = link.get('title')
        linkClasses = link.get('class')
        if linkTitles and type(linkTitles) is list:
            linkTitles = listToString(linkTitles)
        if linkClasses and type(linkClasses) is list:
            linkClasses = listToString(linkClasses)

        # print('link titles: ')
        # print(linkTitles)
        # print('link classes:')
        # print(linkClasses)

        if ((type(linkTitles) is str) and ('pdf' in linkTitles.lower())) \
        or ((type(linkClasses) is str) and ('pdf' in linkClasses.lower())):
            potentialPDFLinks.append(link.get('href'))

    # If there are multiple pdf links, just stop after the first one
    for potentialPDFLink in potentialPDFLinks:
        if downloadPDFFromWebpage(potentialPDFLink, datum, pdfFilePath, newWebpageBaseURL):
            return pdfFilePath
        else:
            return False

def listToString(l):
    listToStr = ' '.join([str(elem) for elem in l])
    return listToStr

def combineListsRemoveDuplicates(l1, l2):
    return l1 + list(set(l2) - set(l1))

def makeListUnique(l):
    return list(dict.fromkeys(l))

def removeEdgeCases(emails):
    emails = [email for email in emails if not isFile(email)]
    emails = [email for email in emails if not lastCharIsNumeric(email)]
    return emails

def isFile(email):
    isFile = False
    for extension in COMMON_FILE_EXTENSIONS:
        if email.endswith(extension):
            isFile = True
            break

    return isFile

def lastCharIsNumeric(email):
    if email[-1].isnumeric():
        return True
    else:
        return False

def downloadPDFFromWebpage(pdfURL, datum, pdfFilePath, newWebpageBaseURL):
    potentialFullURL = newWebpageBaseURL + pdfURL
    URLsToTry = [pdfURL, potentialFullURL]

    for URL in URLsToTry:
        try:
            response = requests.get(URL)
        except requests.exceptions.MissingSchema as e:
            print('href contained partial link, will try appending baseURL...')
        except Exception as e:
            print('Error sending request:')
            print(e)
        except ConnectionResetError as e:
            print('ConnectionResetError!')
            print(e)
        else:
            # If the response directly gave us a PDF, download it and associate the path to the research paper ID in our dict
            print('content type: ' + response.headers['content-type'])
            try:
                contentType, *otherstuff = response.headers['content-type'].split(';')
            except Exception as e:
                print(e)
            else:
                print(contentType)
                if contentType == 'application/pdf':
                    print('Response is a PDF!')
                    datum['downloadedPDFPath'] =  pdfFilePath
                    with open(pdfFilePath, 'wb') as f:
                        f.write(response.content)
                        f.close()
                    return True

    # If we looped through all potential URLs and none of them were PDFs, return false
    return False

def getMetaRefreshRedirectfinalURL(initialURL):
    try:
        response = requests.get(initialURL, allow_redirects=True)
    except Exception as e:
        print('Error trying to figure out final URL')
        print(e)
    else:
        if response.history:
            # print("Request was redirected")
            # for resp in response.history:
            #     print(resp.status_code, resp.url)
            # print("Final destination:")
            # print(response.status_code, response.url, response.headers)

            # print("----------------------------------")

            soup = BeautifulSoup(response.content, 'lxml')

            #print(soup.prettify())

            redirectInputTag = soup.find('input',attrs={'id':'redirectURL'})
            if redirectInputTag:
                print('Found redirect input tag')
                unescapedRedirectURL = redirectInputTag['value']
                escapedRedirectURL = urllib.parse.unquote(unescapedRedirectURL)
                return escapedRedirectURL
            else:
                print('No redirect input tag. Using initial URL')
                return initialURL
        else:
            return initialURL

def get_pdf_paths():
    filenames = []
    for root, dirs, files in os.walk(ROOT_PDFS_PATH):
        for filename in files:
            filenames.append(ROOT_PDFS_PATH + filename)

    return filenames

def parse_pdf(filename):
    print('For:' + filename)
    print()

    #Magic happens with this library...
    try:
        text = textract.process(filename).decode('utf-8')
    except Exception as e:
        print('Error parsing PDF')
        return 'Error parsing PDF'
    else:
        #print(text)
        return find_emails(text)
    finally:
        pass
    
def find_emails(str):
    lst = re.findall(GENERIC_EMAIL_REGEX, str)
    # If we had any matches, print each email
    if lst:
        print('Emails found: ')
        for email in lst:
            print(email)
    else:
        print('No emails found')

    return lst;     


if __name__ == '__main__':
    main(sys.argv[1:])