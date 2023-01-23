from setuptools import find_packages, setup

setup(
    name='mp4arser',
    version='0.1a',
    author='orca.eaa5a',
    #long_description=read('README.md'),
    python_requires='>=3.5',
    #package_data={'mypkg': ['*/requirements.txt']}, # 아직 잘 모르겠음.
    dependency_links = ["https://ffmpeg.org/download.html"], ## 최신 패키지를 설치하는 경우 
    description='mp4 parser specified in live streaming trim',
    packages=find_packages()
)