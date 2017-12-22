import re
import scrapy
from bs4 import BeautifulSoup
from scrapy.http import Request
from news_scrapy.items import DingdianItem,DcontentItem
from news_scrapy.mysqlpipelines.pipelines import Sql

class Myspider(scrapy.Spider):
    name = 'dingdian'
    allowed_domains = ['23us.so']
    bash_url = 'http://www.23us.so/list/'
    bashurl = '.html'


    def start_requests(self):
        for i in range(1,2):
           url = self.bash_url + str(i) + '_1' + self.bashurl
           yield Request(url, self.parse)
        yield Request('http://www.23us.so/full.html',self.parse)

    def parse(self, response):
        max_num = BeautifulSoup(response.text,'lxml').find('div',class_='pagelink').find_all('a')[-1].get_text()
        """print('max_num is ',max_num) 获取http://www.23us.so/list/1_1.html分页里pagelink总页数码
           print(str(response.url))   http://www.23us.so/list/1_1.html
           http://www.23us.so/list/1  """
        bashurl = str(response.url)[:-7]


        for num in range(1, int(max_num) +1):
            url = bashurl + '_' + str(num) + self.bashurl
            """
            print(url)  http://www.23us.so/list/1_1.html
            """
            yield Request(url, callback=self.get_name)


    def get_name(self, response):
        tds = BeautifulSoup(response.text,'lxml').find_all('tr',bgcolor='#FFFFFF')
        for td in tds:
            novelname = td.find('a').get_text()
            #print('小说名字',novelname) #小说名字 巫托邦
            novelurl = td.find('a')['href']
            #print('小说主链接',novelurl)  #小说链接地址  http://www.23us.so/xiaoshuo/19651.html
            yield Request(novelurl,callback=self.get_chapterurl, meta={'name': novelname,'url':novelurl})

    def get_chapterurl(self,response):
        item = DingdianItem() #实例化item.py里定义的item
        item['name'] = str(response.meta['name']).replace('\xa0','') #response.meta['name']是get_name函数传递下来的novelname,novelurl
        item['novelurl'] = response.meta['url'] #'novelurl':'http://www.23us.so/xiaoshuo/19651.html'
        category = BeautifulSoup(response.text,'lxml').find('table').find('a').get_text()
        author = BeautifulSoup(response.text,'lxml').find('table').find_all('td')[1].get_text()
        bash_url = BeautifulSoup(response.text,'lxml').find('p', class_='btnlinks').find('a',class_='read')['href']
        #http://www.23us.so/files/article/html/19/19651/index.html 这里是获得章节的地址
        #print('最新章节地址',bash_url)
        #bash_url  http://www.23us.so/files/article/html/19/19651/index.html 是传给后面callbak的url
        #name_id = 19651
        name_id = str(re.findall(r'^http://.*/\w+/(\w+).html',response.meta['url'])[0]).replace('/','')
        item['category'] = str(category).replace('/','')
        item['author'] = str(author).replace('\xa0','')
        item['name_id'] = name_id
        yield item
        yield Request(url=bash_url,callback=self.get_chapter,meta={'name_id':name_id})

    def get_chapter(self, response):
   #response.text <td class="L"><a href="http://www.23us.so/files/article/html/13/13129/5222261.html">第一章 从天而降的闪电</a></td><td class="L">
        urls = re.findall(r'<td class="L"><a href="(.*?)">(.*?)</a></td>', response.text)
        '''
        [('http://www.23us.so/files/article/html/2/2171/1054756.html', '第一章 九命不死身'), 
        ('http://www.23us.so/files/article/html/2/2171/1054759.html', '第二章 想有就有'),]
        '''
        num = 0
        for url in urls:
            num = num + 1
            chapterurl = url[0]
            chaptername = url[1]

            '''
            #print('章节地址',chapterurl)
            #print('章节名称',chaptername)
            '''
            '''
            chapterurl  is http://www.23us.so/files/article/html/11/11752/4196769.html
            chaptername is 001.梦幻般的花都
            chapterurl  is http://www.23us.so/files/article/html/11/11752/4196770.html
            chaptername is 002.50万欧元的眼镜 
            '''
            rets = Sql.select_chapter(chapterurl)
            if rets[0] == 1:
                print('章节已存在')
                pass
            else:
                yield Request(chapterurl, callback=self.get_chaptercontent, meta={'num':num,
                                                                                  'name_id': response.meta['name_id'],
                                                                                  'chaptername': chaptername,
                                                                                  'chapterurl': chapterurl
                                                                                 })
    def get_chaptercontent(self,response):
        item = DcontentItem()
        item['num'] = response.meta['num']
        item['id_name'] = response.meta['name_id']
        item['chaptername'] = str(response.meta['chaptername']).replace('\xa0', '')
        item['chapterurl'] = response.meta['chapterurl']
        content = BeautifulSoup(response.text, 'lxml').find('dd', id='contents').get_text()
        item['chaptercontent'] = str(content).replace('\xa0', '')
        #print('章节顺序',response.meta['num'])
        #print('小说编号', response.meta['name_id'])
        #print('章节名字', str(response.meta['chaptername']).replace('\xa0',''))
        #print('章节url is',response.meta['chapterurl'])
        return item

