import requests
from pymongo import MongoClient
from scrapy import Selector


class ElectionResults:
    def __init__(self):
        self.initial_url = "https://results.eci.gov.in/Result2021/ConstituencywiseS11115.htm?ac=115"
        self.constituencies = dict()
        self.db = MongoClient()
        self.col = self.db['ElectionResults']['Kerala']
        self.data = []
        self.const_data = dict()

    def get_constituencies(self):
        req = requests.get(self.initial_url)
        sel = Selector(text=req.content)
        constituencies_mixed = sel.xpath('//input[@id="S11"]/@value').extract_first().split(";")
        for const in constituencies_mixed[:-1]:
            key, value = const.split(",")
            self.constituencies[value] = key
        assert len(self.constituencies) == 140
        return self.constituencies

    def read_data(self):
        for name, number in self.constituencies.items():
            self.const_data= dict()
            url = F"https://results.eci.gov.in/Result2021/ConstituencywiseS11{number}.htm?ac={number}"
            req = requests.get(url)
            sel = Selector(text=req.content)
            state_and_const = sel.xpath('//div[@id="div1"]/table[1]/tbody/tr[1]/td/text()').extract_first()
            state_and_const = state_and_const.strip()
            state, const = state_and_const.split("-")
            self.const_data['State'] = state
            self.const_data['Constituency'] = const.title()
            candidates = sel.xpath('''//*[@id='div1']/table[1]/tbody/tr''')
            candidates_list = []
            winner = dict()
            evm_total = 0
            postal_total = 0
            votes_total = 0
            for index, candidate in enumerate(candidates):
                name = candidate.xpath(F'//tr[{index+4}]/td[2]/text()').extract_first()
                if "Total" in name:
                    assert evm_total == int(candidate.xpath(F'//tr[{index+4}]/td[4]/text()').extract_first())
                    assert postal_total == int(candidate.xpath(F'//tr[{index + 4}]/td[5]/text()').extract_first())
                    assert votes_total == int(candidate.xpath(F'//tr[{index + 4}]/td[6]/text()').extract_first())
                    break

                party = candidate.xpath(F'//tr[{index+4}]/td[3]/text()').extract_first()
                evm_votes = int(candidate.xpath(F'//tr[{index+4}]/td[4]/text()').extract_first())
                postal_votes = int(candidate.xpath(F'//tr[{index+4}]/td[5]/text()').extract_first())
                total_votes = int(candidate.xpath(F'//tr[{index+4}]/td[6]/text()').extract_first())
                percent_of_votes = candidate.xpath(F'//tr[{index+4}]/td[7]/text()').extract_first()

                evm_total += evm_votes
                postal_total += postal_votes
                votes_total += total_votes

                data = {
                    'Name': name,
                    'Party': party,
                    'EVM Votes': evm_votes,
                    'Postal Votes': postal_votes,
                    'Total Votes': total_votes,
                    '% of Votes': percent_of_votes,
                }
                if not winner.get('Total Votes', None):
                    winner = data
                elif winner.get('Total Votes') < data['Total Votes']:
                    winner = data
                candidates_list.append(data)

            self.const_data['Candidates'] = candidates_list
            self.const_data['Total EVM Votes'] = evm_total
            self.const_data['Total Postal Votes'] = postal_total
            self.const_data['Total Votes'] = votes_total
            self.const_data['Winning Candidate'] = winner.get('Name')
            self.const_data['Winning Party'] = winner.get('Party')
            self.data.append(self.const_data)
        assert len(self.data) == 140
        self.col.insert(self.data)
        data_file = open('election_data_kerala_2021.json', 'w')
        data_file.write(str(self.data))

    def constituency_trends(self):
        all_data = []
        for i in range(1, 15):
            url = F"https://results.eci.gov.in/Result2021/statewiseS11{i}.htm"
            req = requests.get(url)
            sel = Selector(text=req.content)
            for j in range(0, 10):
                constituency = sel.xpath(F'//*[@id="ElectionResult"]/tr[{j+5}]/td[1]/text()').extract_first()
                constituency_number = int(sel.xpath(F'//*[@id="ElectionResult"]/tr[{j + 5}]/td[2]/text()').extract_first())
                leading_candidate = sel.xpath(F'//*[@id="ElectionResult"]/tr[{j + 5}]/td[3]/text()').extract_first()
                leading_party = sel.xpath(F'//*[@id="ElectionResult"]/tr[{j + 5}]/td[4]/table/tbody/tr/td[1]/text()').extract_first()
                trailing_candidate = sel.xpath(F'//*[@id="ElectionResult"]/tr[{j + 5}]/td[5]/text()').extract_first()
                trailing_party = sel.xpath(F'//*[@id="ElectionResult"]/tr[{j + 5}]/td[6]/table/tbody/tr/td[1]/text()').extract_first()
                margin = int(sel.xpath(F'//*[@id="ElectionResult"]/tr[{j + 5}]/td[7]/text()').extract_first())
                status = sel.xpath(F'//*[@id="ElectionResult"]/tr[{j + 5}]/td[8]/text()').extract_first()
                wining_candidate_2016 = sel.xpath(F'//*[@id="ElectionResult"]/tr[{j + 5}]/td[9]/text()').extract_first()
                wining_party_2016 = sel.xpath(F'//*[@id="ElectionResult"]/tr[{j + 5}]/td[10]/text()').extract_first()
                wining_margin_2016 = int(sel.xpath(F'//*[@id="ElectionResult"]/tr[{j + 5}]/td[11]/text()').extract_first())
                data = {
                    'Constituency': constituency,
                    'Constituency No': constituency_number,
                    'Leading Candidate': leading_candidate,
                    'Leading Party': leading_party,
                    'Trailing Candidate': trailing_candidate,
                    'Trailing Party': trailing_party,
                    'Margin': margin,
                    'Status': status,
                    '2016 Winning Candidate': wining_candidate_2016,
                    '2016 Winning Party': wining_party_2016,
                    '2016 Winning Margin': wining_margin_2016
                }
                all_data.append(data)
        assert len(all_data) == 140
        data_file = open("election_data_trends_2021.json",'w')
        data_file.write(str(all_data))
        self.col.insert(all_data)

if __name__ == "__main__":
    er = ElectionResults()
    er.get_constituencies()
    er.read_data()
    er.constituency_trends()
