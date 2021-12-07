import time

from Proxy import Proxy
from hashlib import md5
import numpy as np
import pickle

class PClient:
    def __init__(self, tracker_addr: (str, int), proxy=None, port=None, upload_rate=0, download_rate=0):
        if proxy:
            self.proxy = proxy
        else:
            self.proxy = Proxy(upload_rate, download_rate, port)  # Do not modify this line!
        self.tracker = tracker_addr
        """
        Start your additional code below!
        """
        self.upload_rate = upload_rate
        self.download_rate = download_rate

    def __send__(self, data: bytes, dst: (str, int)):
        """
        Do not modify this function!!!
        You must send all your packet by this function!!!
        :param data: The data to be send
        :param dst: The address of the destination
        """
        self.proxy.sendto(data, dst)

    def __recv__(self, timeout=None) -> (bytes, (str, int)):
        """
        Do not modify this function!!!
        You must receive all data from this function!!!
        :param timeout: if its value has been set, it can raise a TimeoutError;
                        else it will keep waiting until receive a packet from others
        :return: a tuple x with packet data in x[0] and the source address(ip, port) in x[1]
        """
        return self.proxy.recvfrom(timeout)

    def register(self, file_path: str):
        """
        Share a file in P2P network
        :param file_path: The path to be shared, such as "./alice.txt"
        :return: fid, which is a unique identification of the shared file and can be used by other PClients to
                 download this file, such as a hash code of it
        """
        fid = None
        chunk_size = 128*1024
        """
        Start your code below!
        """
        with open(file_path, "rb") as file:
            content = file.read()

        chunk_num = int(np.ceil(len(content)/chunk_size))
        fid = md5(content).hexdigest()
        chunks = []
        fcid = []
        for i in range(chunk_num):
            left_bound = i*chunk_size
            right_bound = min((i+1)*chunk_size, len(content))
            tmp_chunk = content[left_bound: right_bound]
            tmp_fcid = md5(tmp_chunk).hexdigest()
            fcid.append(tmp_fcid)
            chunks.append(tmp_chunk[:])

        # print(len(chunks[0]), len(chunks[1]))
        # print(len(content))
        trans = {"identifier":"REGISTER", "fid": fid, "fcid": fcid, "rate": self.upload_rate}
        msg = pickle.dumps(trans)
        self.__send__(msg, self.tracker)
        # pass

        """
        End of your code
        """
        return fid

    def register_chunk(self, fid, fcid):
        """

        :param fid:
        :param fcid:
        :return:

        #TODO: add feed back info in the return value
        # NOTE: This the input value should be a str, not a list!!!!!!
        """

        trans = {"identifier":"REGISTER", "fid": fid, "fcid": [fcid], "rate": self.upload_rate}
        msg = pickle.dumps(trans)
        self.__send__(msg, self.tracker)

    def download(self, fid) -> bytes:
        """
        Download a file from P2P network using its unique identification
        :param fid: the unique identification of the expected file, should be the same type of the return value of share()
        :return: the whole received file in bytes
        """
        data = None
        """
        Start your code below!
        """



        """
        End of your code
        """
        return data


    def download_chunk(self, fid, fcid):
        trans = {"identifier": "GET_CHUNK", "fid": fid, "fcid": [fcid]}
        msg = pickle.dumps(trans)
        self.__send__(msg, self.tracker)

    def cancel(self, fid):
        """
        Stop sharing a specific file, others should be unable to get this file from this client any more
        :param fid: the unique identification of the file to be canceled register on the Tracker
        :return: You can design as your need
        """

        pass

        """
        End of your code
        """

    def close(self):
        """
        Completely stop the client, this client will be unable to share or download files any more
        :return: You can design as your need
        """
        pass
        """
        End of your code
        """
        self.proxy.close()


if __name__ == '__main__':
    tracker_address = ("127.0.0.1", 10086)
    B = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    print(B.proxy.port)
    # id = B.register("./test_files/alice.txt")
    msg, frm = B.__recv__()
    print(msg, frm)
    # time.sleep(3)
    # B.register_chunk(id, "testtest123456")
    # msg, frm = B.__recv__()
    # print(msg, frm)
    # pass
