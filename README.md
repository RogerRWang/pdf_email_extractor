# Summary
Extract author emails from COVID-19 research papers stored in a variety of online repositories
Essentially just web crawls the provided links and tries to grab the author email from the page itself, or if it is not on the page, tries to find a download link for the pdf, and then parses the pdf to find the author email.

# Setup
1) Make sure you have python installed: https://www.python.org/downloads/
2) Make sure you have pip installed (it should automatically come with python)
3) We need a few packages:
```
$ pip install requests
$ pip install beautifulsoup4
$ pip install textract
```

# Usage
<b>Format:</b><br>
```
$ python main.py -i <input_tsv_file> -o <output_tsv_file>
```
<b>Example:</b><br>
```
$ python main.py -i part_91_papers_havelink.tsv -o results.tsv
```
You can also use the -h option to show the usage format:
```
$ python main.py -h
usage: main.py -i <inputfile> -o <outputfile>
```

# Input data format
Input must be a TSV (tab separated value) file with the below format (without the actual header!):<br>
|  id  |  something  |  link to paper  |  Title  |
|------|-------------|-----------------|-------------|
| 3xyz |             |  https://doi.org/10.1016/j.jinf.2020.03.021 |  COVID-19 CURE!!!    |

<b>Example:</b><br>
```
3xyz    https://doi.org/10.1016/j.jinf.2020.03.021  COVID-19 CURE!!!
5lizk somefiller  https://doi.org/10.1016/s1473-3099(20)30176-6 COVID-19 SUCKS
```


# Output data format
The output will output a similar TSV file to the file you specify when running the script (The output <i>does</i> have the header):<br>
|  PaperID  |  Emails  |  Link  |
|------|-------------|-----------------|
| 3xyz | \[fauci@nhi.gov, zebra@qq.com, elephant@umich.edu\]            |  https://doi.org/10.1016/j.jinf.2020.03.021 |

<b>Example:</b><br>
```
PaperID	Emails	Link
2ioap802	['shihuanzhong@sina.com', 'pengpengwg@126.com', 'ricusunbing@126.com']	https://journal.chestnet.org/retrieve/pii/S0012369220305584
hsxwz798	['hong-jiang@whu.edu.cn']	http://www.journalofinfection.com/retrieve/pii/S0163445320301468
lz2oqqin	['maxiancang@163.com', 'yadan_wang@hust.edu.com', 'zb_bob@stu.xjtu.edu.cn.']	http://www.journalofinfection.com/retrieve/pii/S0163445320301493
```

# Additional Notes
Running this code will create a `pdfs` folder in the directory to store any PDFs that are downloaded as part of the script. This will make subsequent runs a little faster since it won't have to download the PDF again.

The requests package lets us deal with HTTP requests, responses, redirects, etc in a super easy way.
The beautifulsoup4 package lets us do a lot of web crawling stuff easily.
The textract package is what we use to parse the PDFs in a robust way and find the emails.
