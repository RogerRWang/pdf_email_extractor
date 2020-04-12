import csv
import requests
import re
from bs4 import BeautifulSoup
import PyPDF2
import textract
import os
import urllib

GENERIC_EMAIL_REGEX = '([a-zA-Z0-9._-]+@[a-zA-Z0-9._-]+\.[a-zA-Z0-9_-]{0,3})'
ROOT_PDFS_PATH = 'pdfs/'

def main():

    # Download PDFs
    pdfList = download_pdfs()

    # Populate list of PDFs to parse
    #pdfList = get_pdf_paths()

    # Print our results
    # print('#############################################')
    # print('Final Results')
    # for pdf in pdfList:
    #     print(pdf)


def download_pdfs():
    print('Downloading...')
    alreadyDownloadedPDFs = get_pdf_paths()
    researchPaperData = {}

    # Start building dict of all the associated PDFs for each research paper in the given tsv...
    with open("part_91_papers_havelink.tsv") as tsv:
        reader = csv.reader(tsv, delimiter="\t", quotechar='"')
        for row in reader:
            #column 2 is where the link is
            if row[2]:
                #print(row[2])
                # column 0 is the ID of the research paper
                researchPaperData[row[0]] = {
                    'initialURL': row[2],
                    'finalURL': '',
                    'downloadedPDFPath': '',
                    'emails': []
                }

    # Map research paper ID and the downloaded PDF paths
    for id,datum in researchPaperData.items():
        if id == 'se62cx9w':
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
                        newSplitWebpageURL = urllib.parse.urlparse(response.url);
                        newWebpageBaseURL = newSplitWebpageURL.scheme + '://' + newSplitWebpageURL.netloc
                        print('New webpage base url: ' + newWebpageBaseURL)
                        pdfFilePath = scrapePDFDownloadButtonFromWebpage(response.content, datum, pdfFilePath, newWebpageBaseURL)
                        if pdfFilePath:
                            emails = parse_pdf(pdfFilePath)
                            datum['emails'] = emails
                        else:
                            print('No PDF could be downloaded from webpage')
            else:
                print('No final URL')

    return researchPaperData



def scrapePDFDownloadButtonFromWebpage(webpageContent, datum, pdfFilePath, newWebpageBaseURL):
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
                else:
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
    main()