import sys
import time
from threading import Thread

sys.path.append("../")
from PClient import PClient

tracker_address = ("127.0.0.1", 10086)

if __name__ == '__main__':
    A = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    B = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    C = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    D = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    E = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    fid = A.register("../test_files/alice.txt")
    fid1 = E.register("../test_files/record.mp3")

    files = {}
    files1 = {}
    clients = [B, C, D, E]
    threads1 = []
    threads = []


    # function for download and save
    def download1(node, index):
        files1[index] = node.download(fid1)


    def download(node, index):
        files[index] = node.download(fid)


    for i, client in enumerate(clients):
        threads1.append(Thread(target=download1, args=(clients[i], i)))

    for i, client in enumerate(clients):
        threads.append(Thread(target=download, args=(clients[i], i)))

    time_start = time.time_ns()
    for t in threads:
        t.start()
    for t in threads1:
        t.start()
    for t in threads:
        t.join()
    for t in threads1:
        t.join()

    with open("../test_files/alice.txt", "rb") as bg:
        bs = bg.read()
        for i in files:
            if files[i] != bs:
                raise Exception()

    with open("../test_files/record.mp3", "rb") as bg:
        bs = bg.read()
        for i in files:
            if files1[i] != bs:
                raise Exception()

    A.close()
    B.close()
    C.close()
    D.close()
    E.close()




