import json
import datetime
import csv
import time
import facebook
from time import gmtime, strftime

try:
    from urllib.request import urlopen, Request
except ImportError:
    from urllib2 import urlopen, Request

app_id = "1491500724232517"
app_secret = "206eddb6534f9bd73c55556087767170"  # DO NOT SHARE WITH ANYONE!
file_id = "2017-01-012017-12-31"

#access_token = app_id + "|" + app_secret
access_token = "EAACEdEose0cBAF5Uq1Nlv1uOAzC6fnZARl66GyFsNMi0KpgwnZCiZAlXAZAQ81KmZBKQNvgHu47Ieojqx4ZBtb8urC3KKj1RkCwX6gVTRzYF2FtN8X66BtxK0ZCIrn1qsjmLIZB7U5pmcZCKZA8yo37NkXJerzyfXtfDC95u7utUWaz4KZCz1BH0sTq7ZCEfSW2B8B5m14z4NfWvWgZDZD"

token = access_token
graph = facebook.GraphAPI(access_token=token, version='2.9')



# Needed to write tricky unicode correctly to csv


def unicode_decode(text):
    try:
        return text.encode('utf-8').decode()
    except UnicodeDecodeError:
        return text.encode('utf-8')


def getFacebookCommentFeedUrl():

    # Construct the URL string
    fields = "id,message,reactions.limit(0).summary(true)" + \
        ",created_time,from,comments,attachment"
    
    return fields



def getReactionsForComments(base_url):

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


def processFacebookComment(comment, status_id, parent_id=''):
    
    # The status is now a Python dictionary, so for top-level items,
    # we can simply call the key.

    # Additionally, some items may not always exist,
    # so must check for existence first
    
    comment_id = comment['id']
    comment_message = '' if 'message' not in comment or comment['message'] \
        is '' else unicode_decode(comment['message'])
    #comment_author = unicode_decode(comment['from']['name'])
    #author_id = unicode_decode(comment['from']['id'])
    

    num_reactions = 0 if 'reactions' not in comment else \
        comment['reactions']['summary']['total_count']

    if 'attachment' in comment:
        attachment_type = comment['attachment']['type']
        attachment_type = 'gif' if attachment_type == 'animated_image_share' \
            else attachment_type
        attach_tag = "[[{}]]".format(attachment_type.upper())
        comment_message = attach_tag if comment_message is '' else \
            comment_message + " " + attach_tag

    # Time needs special care since a) it's in UTC and
    # b) it's not easy to use in statistical programs.

    comment_published = datetime.datetime.strptime(
        comment['created_time'], '%Y-%m-%dT%H:%M:%S+0000')
    comment_published = comment_published + datetime.timedelta(hours=-5)  # EST
    comment_published = comment_published.strftime(
        '%Y-%m-%d %H:%M:%S')  # best time format for spreadsheet programs

    # Return a tuple of all processed data

    return (comment_id, status_id, parent_id, comment_message,
            comment_published, num_reactions)


def scrapeFacebookPageFeedComments(page_id, access_token):
    with open('{}facebook_comments.csv'.format(file_id), 'w') as file:
        w = csv.writer(file)
        w.writerow(["comment_id", "status_id", "parent_id", "comment_message", 
                    "comment_published", "num_reactions",
                    "num_likes", "num_loves", "num_wows", "num_hahas",
                    "num_sads", "num_angrys"])

        num_processed = 0
        scrape_starttime = datetime.datetime.now()
        after = ''
        
        print("Scraping {} Comments From Posts: {}\n".format(
            file_id, scrape_starttime))

        with open('{}facebook_statuses.csv'.format(file_id), 'r') as csvfile:
            reader = csv.DictReader(csvfile)

            # Uncomment below line to scrape comments for a specific status_id
            # reader = [dict(status_id='5550296508_10154352768246509')]

            for status in reader:
                has_next_page = True
                while has_next_page:
                    node = "/{}/comments".format(status['status_id'])
                    
                    after = '' if after is '' else "?after={}".format(after)
                    base_url =  node +after


                    commentFields = getFacebookCommentFeedUrl()
                    # print(url)
                    
                    comments = graph.get_object(base_url,fields=commentFields)
                    
                        
                    #comments = json.loads(dataresponse)
                    reactions = getReactionsForComments(base_url)

                    for comment in comments['data']:
                        
                        comment_data = processFacebookComment(
                            comment, status['status_id'])
                        reactions_data = reactions[comment_data[0]]

                        # calculate thankful/pride through algebra
                        w.writerow(comment_data + reactions_data )


                        if 'comments' in comment:
                            has_next_subpage = True
                            sub_after = ''

                            while has_next_subpage:
                                sub_node = "/{}/comments".format(comment['id'])
                                sub_after = '' if sub_after is '' else "?after={}".format(
                                    sub_after)
                                
                                sub_base_url = sub_node  + sub_after

                                sub_comment_fields = getFacebookCommentFeedUrl()
                                sub_comments = graph.get_object(sub_base_url,fields=sub_comment_fields)


                                #sub_comments = json.loads(sub_comment_response)
                                sub_reactions = getReactionsForComments(sub_base_url)

                                for sub_comment in sub_comments['data']:
                                    sub_comment_data = processFacebookComment(
                                        sub_comment, status['status_id'], comment['id'])
                                    sub_reactions_data = sub_reactions[
                                        sub_comment_data[0]]


                                    w.writerow(sub_comment_data +
                                               sub_reactions_data)

                                    num_processed += 1
                                    if num_processed % 100 == 0:
                                        print("{} Comments Processed: {}".format(
                                            num_processed,
                                            datetime.datetime.now()))

                                if 'paging' in sub_comments:
                                    if 'next' in sub_comments['paging']:
                                        sub_after = sub_comments[
                                            'paging']['cursors']['after']
                                    else:
                                        has_next_subpage = False
                                else:
                                    has_next_subpage = False

                        # output progress occasionally to make sure code is not
                        # stalling
                        num_processed += 1
                        if num_processed % 100 == 0:
                            print("{} Comments Processed: {}".format(
                                num_processed, datetime.datetime.now()))

                    if 'paging' in comments:
                        if 'next' in comments['paging']:
                            after = comments['paging']['cursors']['after']
                        else:
                            has_next_page = False
                            after = ''
                    else:
                        has_next_page = False
                        after = ''

        print("\nDone!\n{} Comments Processed in {}".format(
            num_processed, datetime.datetime.now() - scrape_starttime))


if __name__ == '__main__':
    
    current_date = strftime("%Y-%m-%d", gmtime())

    file_id = ''
    scrapeFacebookPageFeedComments(file_id, access_token)