import sys
import time

sys.path.append("../")
from PClient import PClient
from threading import Thread

tracker_address = ("127.0.0.1", 10086)

if __name__ == '__main__':
    # A,B join the network
    A = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    B = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    print("A",A.proxy.port)
    print("B",B.proxy.port)

    C = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    print("C", C.proxy.port)
    # data2 = C.download(fid)

    # A register a file and B download it
    fid = A.register("../test_files/alice.txt")
    # data1 = B.download(fid)
    # A cancel the register of the file
    clients = [B, C]
    threads = []
    files = {}

    def download(node, index):
        files[index] = node.download(fid)

    for i, client in enumerate(clients):
        threads.append(Thread(target=download, args=(client, i)))

    print("B starts!")
    threads[0].start()

    time.sleep(1)
    print("A cancel!")
    # A.close()
    A.cancel(fid)

    time.sleep(1)
    print("C starts!")
    threads[1].start()


    # C join the network and download the file from B

    time.sleep(5)
    print("A come back!")
    A.register("../test_files/alice.txt")


    for t in threads:
        t.join()
    print(files[0])
    # for i in files:
    #     if files[i] != bs:
    #         raise Exception("Downloaded file is different with the original one")
    # print("SUCCESS")


    # if data1 == data2:
    #     print("Success!")
    # else:
    #     raise RuntimeError

    B.close()
    C.close()
    A.close()