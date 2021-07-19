import os
import time
import random
import pandas as pd
import numpy as np

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException

"""
整個爬蟲分三個步驟:
1.先把所有題目跟url爬下來。產出為`questions.csv`
2.分別點開每個題目的url去補評分, 此步驟耗時最長 and 有可能被短暫的ban掉。產出為`questions_with_rating.csv`
3.再回頭去爬category幫題目上標籤。產出為`questions_with_tag.csv`
"""


def print_elements(elements):
    """
    DEBUG TOOL:
    Print WebElements outerHTML
    """
    for i, element in enumerate(elements):
        print(i, element.get_attribute('outerHTML'))


def parse_questions():
    driver = webdriver.Chrome('./chromedriver')
    driver.get('https://leetcode.com/problemset/algorithms/')
    time.sleep(3)

    arr_data = []

    page_num = 1
    while True:
        print("\npage:", page_num)
        page_num += 1

        # Get page questions
        try:
            time.sleep(2)
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//tr[@data-row-key]")))
        except TimeoutException:
            print("timeout")
        page_questions_rows = driver.find_elements_by_xpath("//tr[@data-row-key]")

        # Handle rows
        for i, row in enumerate(page_questions_rows):
            try:
                cols = row.find_elements_by_tag_name("td")

                tag_a = cols[1].find_element_by_tag_name("a")

                question_url = tag_a.get_property("href")
                if "/explore/" in question_url:  # we don't want `explore question`
                    continue

                title = tag_a.text
                title_split = title.split('. ')

                question_id = title_split[0]
                question_title = "".join(title_split[1::])

                acceptance = cols[3].text
                difficulty = cols[4].text

                premium = 1
                tmp = cols[1].find_elements_by_tag_name("svg")
                if len(tmp) > 0:
                    premium = 0

                data = {
                    'id': question_id,
                    'title': question_title,
                    'url': question_url,
                    'acceptance': acceptance,
                    'difficulty': difficulty,
                    'premium': premium,
                }
                print("{:02d}".format(i), data)
                arr_data.append(data)

            except Exception as e:
                print(e)
                driver.quit()

        next_button = driver.find_elements_by_xpath("//nav[@role='navigation']/button")[-1]  # Next page
        if not next_button.is_enabled():  # last page
            break

        next_button.click()

    # Save data
    df = pd.DataFrame(arr_data)
    df.to_csv('./questions.csv', index=False)
    print("Parse questions done.")
    driver.quit()


def parse_rating():
    """
    Leetcode might block us if we have too many requests in a period of time.
    So we might do it in batch, save csv file every time after we got response,
    then next time we can skip those url we have done.

    If we want to update the rating, just delete "like" and "dislike" columns and then parse it again,
    or just delete `questions_with_rating.csv` file.
    """

    driver = webdriver.Chrome('./chromedriver')

    if os.path.isfile('./questions_with_rating.csv'):
        df = pd.read_csv('./questions_with_rating.csv')
    else:
        df = pd.read_csv('./questions.csv')

    # Add empty "like" and "dislike" columns if not exist
    if "like" not in df.columns:
        df["like"] = ""
    if "dislike" not in df.columns:
        df["dislike"] = ""

    for i in range(len(df)):
        data = df.iloc[i]

        if data['premium'] == 1:  # We don't parse premium questions
            continue

        if data["like"] or data["dislike"]:
            continue

        # Send request
        driver.get(data['url'])
        time.sleep(random.randint(1, 7))
        try:
            WebDriverWait(driver, 300).until(
                EC.presence_of_element_located((By.XPATH, "//div[@data-cy='question-title']/../div")))
        except TimeoutException:
            print("timeout")

        element = driver.find_elements_by_xpath("//div[@data-cy='question-title']/../div")[1]
        btn_arr = element.find_elements_by_tag_name("button")
        like = btn_arr[0].text
        dislike = btn_arr[1].text

        # Fill data
        df.loc[i, 'like'] = like
        df.loc[i, 'dislike'] = dislike
        print(data["id"], data["title"])

        # Save data
        df.to_csv('./questions_with_rating.csv', index=False)

    print("Parse rating done.")
    driver.quit()


def parse_tag():
    driver = webdriver.Chrome('./chromedriver')

    if os.path.isfile('./questions_with_tag.csv'):
        df = pd.read_csv('./questions_with_tag.csv')
    else:
        df = pd.read_csv('./questions_with_rating.csv')

    # Add empty "tag" columns if not exist
    if "tag" not in df.columns:
        df["tag"] = ""

    # First we need to get the category list from the main page.
    driver.get('https://leetcode.com/problemset/all/')
    time.sleep(random.randint(1, 7))
    try:
        WebDriverWait(driver, 300).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/tag/')]")))
    except TimeoutException:
        print("timeout")

    tags = driver.find_elements_by_xpath("//a[contains(@href, '/tag/')]")
    urls = []
    for tag in tags:
        url = tag.get_attribute("href")
        print(url)
        urls.append(url)

    # Start parsing tag pages
    for url in urls:
        tag = url.replace("https://leetcode.com/tag/", "") + ";"
        print("==={}===".format(tag))

        driver.get(url)
        time.sleep(random.randint(1, 7))
        try:
            WebDriverWait(driver, 300).until(
                EC.presence_of_element_located((By.XPATH, "//tbody[@class='reactable-data']")))
        except TimeoutException:
            print("timeout")

        rows = driver.find_elements_by_xpath("//tbody[@class='reactable-data']/tr")
        for row in rows:
            cols = row.find_elements_by_tag_name("td")

            # We only need id in this task. Other informations is the same as "all question" page.
            id = np.int(cols[1].text)

            try:
                if id in df['id']:
                    df.loc[df['id'] == id, 'tag'] = df.loc[df['id'] == id, 'tag'] + tag
                else:
                    print("Id not found in df:", id)
                    raise IndexError()

            except Exception as e:
                print(e)

    # Save data
    df.to_csv('./questions_with_tag.csv', index=False)
    print("Parse tag done.")
    driver.quit()


def main():
    # parse_questions()
    # parse_rating()
    # parse_tag()
    print("All tasks completed.")


if __name__ == "__main__":
    main()
