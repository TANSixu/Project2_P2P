import sys
sys.path.append("../")
from Project2_P2P.PClient import PClient

tracker_address = ("127.0.0.1", 10086)

if __name__ == '__main__':
    # A,B join the network
    A = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    B = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    print("A",A.proxy.port)
    print("B",B.proxy.port)
    # A register a file and B download it
    fid = A.register("../test_files/alice.txt")
    data1 = B.download(fid)
    # A cancel the register of the file
    A.close()
    print("flag!")
    # C join the network and download the file from B
    C = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    print("C", C.proxy.port)
    data2 = C.download(fid)

    if data1 == data2:
        print("Success!")
    else:
        raise RuntimeError

    B.close()
    C.close()
