import numpy as np

from Project2_P2P.PClient import PClient
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
            #trans = {"identifier":"REGISTER", "fid": fid, "fcid": fcid, "rate": self.upload_rate}
            if msg["identifier"] == "REGISTER":
                fid = msg["fid"]
                if fid not in self.file.keys():
                    self.file[fid] = {}
                fcid=msg["fcid"]
                for item in fcid:
                    if item not in self.file[fid].keys():
                        self.file[fid][item]=[]
                    pclient=(frm,msg["rate"])
                    self.file[fid][item].append(pclient)
                self.response("Success", frm)

            # elif msg.startswith("QUERY:"):
            #     # Client can use this to check who has the specific file with the given fid
            #     fid = msg[6:]
            #     result = []
            #     for c in self.file[fid]:
            #         result.append(c)
            #     self.response("[%s]" % (", ".join(result)), frm)
            #
            # elif msg.startswith("CANCEL:"):
            #     # Client can use this file to cancel the share of a file
            #     fid = msg[7:]
            #     if client in self.files[fid]:
            #         self.files[fid].remove(client)
            #     self.response("Success", frm)


    def response(self, data: str, address: (str, int)):
        self.__send__(data.encode(), address)


if __name__ == '__main__':
    tracker = Tracker(port=10086)
    tracker.start()
