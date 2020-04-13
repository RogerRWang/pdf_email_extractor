# pdf_email_extractor
Extract author emails from COVID-19 research papers stored in a variety of online repositories
Essentially just web crawls the provided links and tries to grab the author email from the page itself, or if it is not on the page, tries to find a download link for the pdf, and then parses the pdf to find the author email.

# Usage
$python main.py -i \<input tsv file\> -o \<output tsv file\>
<br><br>
<b>Example:</b><br>
$python main.py -i part_91_papers_havelink.tsv -o results.tsv


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
