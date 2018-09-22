import json
import datetime
import csv
import time
import datetime
import facebook
from time import gmtime, strftime

try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request



app_id = "1358232680947619"
app_secret = "a25b07c359baa3022ecfe3bb740f89c2"  #app_secret avoid sharing this attribute with others
page_id = "ooredoodz"





access_token = "EAACEdEose0cBAJy8P8GVg01N90ZAPAwF6BTT4DF57PJIJY59VSF2QqSLMUruyENUdHlEZBodUAnQZAyBBfJgpWR5fQzG4SyJzZA8GMAxZA6PbMd7aXrAEoU6ZCUlJLzDAJd9ce8lTwNs49c3V5ZAoPdnStLYfB3TLeL0mlEEwOzKQe3KMA52UxMn1Jhi4jVLcUGsOhqaPQDdQZDZD"
token = access_token
graph = facebook.GraphAPI(access_token=token,version='2.9')

#Decode complexe  unicode text
def unicode_decode(text):
    try:
        return text.encode('utf-8').decode()
    except UnicodeDecodeError:
        return text.encode('utf-8')



def processFacebookPageFeedStatus(status):

    # The status is now a Python dictionary, so for top-level items,
    # we can simply call the key.

    # Additionally, some items may not always exist,
    # so must check for existence first

    status_id = status['id']
    status_type = status['type']

    status_message = '' if 'message' not in status else \
        unicode_decode(status['message'])
    link_name = '' if 'name' not in status else \
        unicode_decode(status['name'])
    status_link = '' if 'link' not in status else \
        unicode_decode(status['link'])

    # Time needs special care since a) it's in UTC and
    # b) it's not easy to use in statistical programs.

    status_published = datetime.datetime.strptime(
        status['created_time'], '%Y-%m-%dT%H:%M:%S+0000')
    status_published = status_published + \
        datetime.timedelta(hours=-5)  # EST
    status_published = status_published.strftime(
        '%Y-%m-%d %H:%M:%S')  # best time format for spreadsheet programs

    # Nested items require chaining dictionary keys.

    num_reactions = 0 if 'reactions' not in status else \
        status['reactions']['summary']['total_count']
    num_comments = 0 if 'comments' not in status else \
        status['comments']['summary']['total_count']
    num_shares = 0 if 'shares' not in status else status['shares']['count']

    return (status_id, status_message, link_name, status_type, status_link,
            status_published, num_reactions, num_comments, num_shares)



def getFacebookPageFeedUrl():

        # Reactions parameters
    fields = "message,link,created_time,type,name,id," + \
        "comments.limit(0).summary(true),shares,reactions" + \
        ".limit(0).summary(true)"

    return fields

def getReactionsForStatuses(base_url):

    reaction_types = ['like', 'love', 'wow', 'haha', 'sad', 'angry']
    reactions_dict = {}   # dict of {status_id: tuple<6>}

    for reaction_type in reaction_types:
        fields = "reactions.type({}).limit(0).summary(total_count)".format(
            reaction_type.upper())


        response_reaction = graph.get_object(base_url,fields=fields)

        data = response_reaction['data']

        data_processed = set()  # set() removes rare duplicates in statuses
        for status in data:
            id = status['id']
            count = status['reactions']['summary']['total_count']
            data_processed.add((id, count))

        for id, count in data_processed:
            if id in reactions_dict:
                reactions_dict[id] = reactions_dict[id] + (count,)
            else:
                reactions_dict[id] = (count,)

    return reactions_dict




def scrapeFacebookPageFeedStatus(page_id, access_token, since_date, until_date):
    with open('facebook_statuses.csv', 'w') as file:
        w = csv.writer(file)
        w.writerow(["status_id", "status_message", "link_name", "status_type",
                    "status_link", "status_published", "num_reactions",
                    "num_comments", "num_shares", "num_likes", "num_loves",
                    "num_wows", "num_hahas", "num_sads", "num_angrys",
                    "num_special"])

        has_next_page = True
        num_processed = 0
        scrape_starttime = datetime.datetime.now()
        node = "{}/posts".format(page_id)
        after = ''



        print("Scraping {} Facebook Page: {}\n".format(page_id, scrape_starttime))

        while has_next_page:


            #d = time.strptime(since_date[:-1], "%Y-%m-%d")    
            #d = datetime.date(d.tm_year,d.tm_mon,d.tm_mday)        
            #since = int (time.mktime(d.timetuple()))

            #d = time.strptime(until_date[:-1], "%Y-%m-%d")     
            #d = datetime.date(d.tm_year,d.tm_mon,d.tm_mday)        
            #until = int (time.mktime(d.timetuple()))

            after = '' if after is '' else "&after={}".format(after)

            base_url =  node + "?since="+since_date+"&until="+ until_date + after


            since = "&since={}".format(since_date) if since_date \
            is not '' else ''
            
            until = "&until={}".format(until_date) if until_date \
            is not '' else ''

            post_fields = getFacebookPageFeedUrl()

            statuses = graph.get_object(base_url,fields=post_fields)

            reactions = getReactionsForStatuses(base_url)

            for status in statuses['data']:

                # Ensure it is a status with the expected metadata
                if 'reactions' in status:
                    status_data = processFacebookPageFeedStatus(status)
                    reactions_data = reactions[status_data[0]]

                    # calculate thankful/pride through algebra
                    num_special = status_data[6] - sum(reactions_data)
                    w.writerow(status_data + reactions_data + (num_special,))

                num_processed += 1
                if num_processed % 100 == 0:
                    print("{} Statuses Processed: {}".format
                          (num_processed, datetime.datetime.now()))

            # if there is no next page, we're done.

            if 'paging' in statuses:
               after = statuses['paging']['cursors']['after']
            else:
                has_next_page = False

        print("\nDone!\n{} Statuses Processed in {}".format(
              num_processed, datetime.datetime.now() - scrape_starttime))


if __name__ == '__main__':
    # input date formatted as YYYY-MM-DD
    until_date = strftime("%Y/%m/%d", gmtime())

    with open("date-execute.txt", 'r') as f:
        since_date = f.readlines()[-1]

    with open("date-execute.txt", 'a') as f:
        f.write(until_date + "\n")


    scrapeFacebookPageFeedStatus(page_id, access_token, since_date, until_date)
