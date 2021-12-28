import time
from threading import Thread
import sys
sys.path.append("../")
from PClient import PClient

tracker_address = ("127.0.0.1", 10086)


if __name__ == '__main__':
    # A,B,C,D,E join the network
    A = PClient(tracker_address, upload_rate=110000, download_rate=50000)
    C = PClient(tracker_address, upload_rate=890000, download_rate=100000)
    D = PClient(tracker_address, upload_rate=90000, download_rate=100000)
    E = PClient(tracker_address, upload_rate=80000, download_rate=100000)
    F = PClient(tracker_address, upload_rate=120000, download_rate=100000,port=38438)
    G = PClient(tracker_address, upload_rate=60000, download_rate=100000)
    H = PClient(tracker_address, upload_rate=50000, download_rate=100000)
    print(A.proxy.port)
    print(C.proxy.port)
    print(D.proxy.port)
    print(E.proxy.port)
    print(F.proxy.port)
    print(G.proxy.port)
    print(H.proxy.port)


    clients = [C, D, E,F,G,H]
    # A register a file and B download it
    fid = A.register("../test_files/bg.png")
    threads = []
    files = {}

    # function for download and save
    def download(node, index):
        files[index] = node.download(fid)

    time_start = time.time_ns()
    for i, client in enumerate(clients):
        threads.append(Thread(target=download, args=(client, i)))
    # start download in parallel
    for t in threads:
        t.start()

    time.sleep(80)
    print("one change")
    C.proxy.upload_rate = 65000

    time.sleep(60)
    print("two change")
    C.proxy.upload_rate = 900000
    # wait for finish
    for t in threads:
        t.join()
    # check the downloaded files
    with open("../test_files/bg.png", "rb") as bg:
        bs = bg.read()
        for i in files:
            if files[i] != bs:
                raise Exception("Downloaded file is different with the original one")

    A.close()

    C.close()
    D.close()
    E.close()
    F.close()
    G.close()
    H.close()

    print((time.time_ns() - time_start) * 1e-9)
