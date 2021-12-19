import numpy as np
from PClient import PClient
from Proxy import Proxy
import pickle


class Tracker:
    def __init__(self, upload_rate=10000, download_rate=10000, port=None):
        self.proxy = Proxy(upload_rate, download_rate, port)
        self.file = {}  # file=[{file1_1:chunk1....}{file1_2:......}]
        self.client_rate = {}  # key:frm value:rate

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

    def start(self):
        """
        Start the Tracker, and it will work forever
        :return: None
        """
        while True:
            msg, frm = self.__recv__()
            msg = pickle.loads(msg)
            if msg["identifier"] == "REGISTER":
                # trans = {"identifier":"REGISTER", "fid": fid, "fcid": fcid, "rate": self.upload_rate}
                fid = msg["fid"]
                if fid not in self.file.keys():
                    self.file[fid] = {}
                fcid = msg["fcid"]
                for item in fcid:
                    if item not in self.file[fid].keys():
                        self.file[fid][item] = []
                    self.file[fid][item].append(frm)
                    if frm not in self.client_rate.keys():
                        self.client_rate[frm] = msg["rate"]
                # 不删去会有影响
                # self.response("Success", frm)
                print(self.file)
            elif msg["identifier"] == "QUERY":
                # Client can use this to check who has the specific file with the given fid
                # trans = {"identifier":"QUERY", "fid": fid}
                fid = msg["fid"]
                keys = list(self.file[fid].keys())
                transfer = {"identifier": "QUERY_RESULT_INITIAL", "fid": fid, "result": keys}
                ans = pickle.dumps(transfer)
                self.__send__(ans, frm)
            elif msg["identifier"] == "QUERY_TRUNK":
                # tran = {"identifier": "QUERY_TRUNK", "fid": fid, "fcid": fcid}
                fid = msg["fid"]
                fcid = msg["fcid"]
                cilents = self.file[fid][fcid]
                result = []
                for item in cilents:
                    result.append((item, self.client_rate[item]))
                transfer = {"identifier": "QUERY_RESULT_EACH", "fid": fid, "fcid": fcid, "result": result}
                ans = pickle.dumps(transfer)
                self.__send__(ans, frm)

            elif msg["identifier"] == "CANCEL:":
                # Client can use this file to cancel the share of a file
                # trans = {"identifier":"CANCEL", "fid": fid}
                fid = msg["fid"]
                registered_chunk = self.file[fid]
                for chunk in registered_chunk.keys():
                    for client in registered_chunk[chunk]:
                        if client[0] == frm:
                            registered_chunk[chunk].remove(client)
                self.response("Success", frm)
            elif msg["identifier"] == "CHANGE_RATE":
                self.client_rate[frm] = msg["rate"]
                self.response("Success", frm)

    def response(self, data: str, address: (str, int)):
        self.__send__(data.encode(), address)


if __name__ == '__main__':
    tracker = Tracker(port=10086)
    tracker.start()
