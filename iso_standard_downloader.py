import os
import re

import click as click
import requests

from bs4 import BeautifulSoup
from tqdm import tqdm


class IsoStandards:
    def __init__(self):
        self.BASE_URL = 'https://standards.iso.org'
        self.PATH = './downloads/'

        self.s = requests.session()
        # jesus christ
        self.pattern = re.compile(r'(iso)[^/]*/(\d+)/(-\d+)/([^/]+)')

    def check_url(self, iso_url: str) -> bool:
        if not iso_url.startswith(self.BASE_URL):
            return False

        return True

    def raw_get_html(self, link: str) -> None or bytes:
        try:
            r = self.s.get(link, stream=True)

            if r.status_code == 200 and r.headers['Content-Type'].lower() is not None:
                return r.content

            return None

        except requests.RequestException as e:
            print('Error during requests to {0} : {1}'.format(link, str(e)))
            return None

    def download_file(self, file_url: str, base_url: str, show_progress: bool = False):
        """
        Downloads a single file to self.PATH using requests and tqdm
        :param file_url: The file_url which gets downloaded
        :param base_url: The base_url of the downloaded folder, so it will calulate the relative path from both
        :param show_progress: True for enabling a progress bar with tqdm
        :return:
        """
        # remove the base_url from the file_url to get the actual relative path
        file_path = os.path.join(self.PATH, file_url.replace(base_url, ''))
        if os.path.exists(file_path):
            print(f'Already downloaded {file_path}')
            return

        # extract the folder_path from the file_path and create those folders
        folder_path = os.path.dirname(file_path)
        os.makedirs(folder_path, exist_ok=True)

        print(f'Downloading {file_path}')
        # stream the file with error handling
        try:
            r = self.s.get(file_url, stream=True)
            if r.status_code != 200 or r.headers['Content-Type'].lower() is None:
                return

        except requests.RequestException as e:
            print('Error during requests to {0} : {1}'.format(file_url, str(e)))
            return None

        try:
            total = int(r.headers['content-length'])
        except KeyError:
            return

        with open(file_path, 'wb') as f:
            # just use the tdqm progress bar
            if show_progress:
                with tqdm(total=total, unit='B', unit_scale=True, unit_divisor=1024, miniters=1) as bar:
                    for chunk in r.iter_content(chunk_size=1024):
                        # filter out keep-alive new chunks
                        if chunk:
                            f.write(chunk)
                            bar.update(len(chunk))
            else:
                for chunk in r.iter_content(chunk_size=1024):
                    # filter out keep-alive new chunks
                    if chunk:
                        f.write(chunk)

    def load_folder(self, folder_url: str, base_url: str):
        """
        Recursive function which will load all folders from a parent folder

        :param folder_url: The actual URL of the folder
        :param base_url: The base URL of the main folder
        :return:
        """
        raw_html = self.raw_get_html(folder_url)
        soup = BeautifulSoup(raw_html, 'html.parser')

        # get the table and all table rows
        table = soup.find('tbody')
        table_rows = table.find_all('tr')

        # iterate over all table rows (files and folders)
        for row in table_rows:
            # get the data_type which is either fa-file or fa-folder
            data_type = row.find('td').get('data-sort')
            # save the relative path
            children_url = row.find('a').get('href')
            # convert it to an absolute path
            actual_url = self.BASE_URL + children_url

            if 'folder' in data_type:
                # recursively open the new-found folder
                self.load_folder(actual_url, base_url)
            elif 'file' in data_type:
                # download the file if it's not a folder
                self.download_file(actual_url, base_url)
            else:
                print('Unknown file type, skipping')

    @click.command(
        name='ISO-Standards-Downloader',
        short_help='A python module to download ISO Standards from https://standards.iso.org/iso-iec',
        context_settings=dict(
            help_option_names=['-?', '-h', '--help']
        ))
    @click.argument(
        'iso_url',
        type=str
    )
    def main(self, iso_url: str):
        """
        ISO_URL: Enter the URL from the ISO Standard you want to download: https://standards.iso.org/iso-iec

        \f
        :param iso_url: URL from https://standards.iso.org/iso-iec
        :return: Nothing
        """
        if not self.check_url(iso_url):
            print(f'Enter a valid ISO Standards URL starting with: {self.BASE_URL}')
            exit()

        # remove the base url and perform an iso standard beautifier
        iso_name = iso_url.replace(self.BASE_URL, "")[1:]
        try:
            iso_name = ' '.join(x for x in re.findall(self.pattern, iso_name)[0]).upper()
        except IndexError:
            print('Could not beautify the URL, continuing anyway')

        # save the new path in self.PATH
        self.PATH = os.path.join(self.PATH, iso_name)

        print(f'Found ISO Standard: {iso_name}')
        self.load_folder(iso_url, base_url=iso_url)
        print('Download finished!')


if __name__ == '__main__':
    iso_standards = IsoStandards()
    iso_standards.main()
