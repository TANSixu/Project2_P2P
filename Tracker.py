import numpy as np

from PClient import PClient
from Proxy import Proxy
import pickle


class Tracker:
    def __init__(self, upload_rate=10000, download_rate=10000, port=None):
        self.proxy = Proxy(upload_rate, download_rate, port)
        self.file = {}
        # file=[{file1_1:chunk1....}{file1_2:......}]

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
        Start the Tracker and it will work forever
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
                    pclient = (frm, msg["rate"])
                    self.file[fid][item].append(pclient)
                self.response("Success", frm)
                print(self.file)
            elif msg["identifier"] == "QUERY":
                # Client can use this to check who has the specific file with the given fid
                # trans = {"identifier":"QUERY", "fid": fid}
                fid = msg["fid"]
                result = {}
                keys = self.file[fid].keys()
                for c in keys:
                    values = self.file[fid][c]
                    result[c] = values

                #     fast = 0
                #     fast_index = 0
                #     for index, x in enumerate(values):
                #         if x[1] > fast:
                #             fast = x[1]
                #             fast_index = index
                #     result[c].append(values[fast_index][0][0])
                #     result[c].append(values[fast_index][0][1])
                #     result[c].append(values[fast_index][1])
                # #self.response("[%s]" % (", ".join(result)), frm)
                ans = pickle.dumps(result)
                self.__send__(ans, frm)
            #
            elif msg["identifier"] == "CANCEL:":
                # Client can use this file to cancel the share of a file
                #  # trans = {"identifier":"CANCEL", "fid": fid, "fcid": fcid }
                fid = msg["fid"]
                fcid = msg["fcid"]
                registered_chunk = self.file[fid]
                for trunk in fcid:
                    for client in registered_chunk[trunk]:
                        if client[0] == frm:
                            registered_chunk[trunk].remove(client)
                self.response("Success", frm)


    def response(self, data: str, address: (str, int)):
        self.__send__(data.encode(), address)


if __name__ == '__main__':
    tracker = Tracker(port=10086)
    tracker.start()
