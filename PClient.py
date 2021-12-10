import time

from Proxy import Proxy
from hashlib import md5
import numpy as np
import pickle
from queue import SimpleQueue
from threading import Thread


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
        self.file = {}  # key: fid, fcid ; values: corresponding bytes

        # self.tracker_buffer = SimpleQueue()  # message from tracker ()
        self.tracker_buffer = {}  # key:fid value:simpleQueue

        self.peer_query_buffer = SimpleQueue()  # message from other PClient (other PClient query you)

        # self.peer_respond_buffer = SimpleQueue()  # messqge from other PClient (you query other PClient)
        self.peer_respond_buffer = {}  # key = fcid value= simplequeue

        # Thread(target=self.listening(), args=()).start()  # thread to receive and divide message
        self.provide = Thread(target=self.provide_to_peer(), args=()) # thread to provide trunk to peer
        # self.provide.start()
        self.my_file = []  #records of my_file

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
        # fid = None
        chunk_size = 128 * 1024
        """
        Start your code below!
        """
        with open(file_path, "rb") as file:
            content = file.read()

        chunk_num = int(np.ceil(len(content) / chunk_size))
        fid = md5(content).hexdigest()
        chunks = []
        self.file[fid] = {}
        fcid = []
        for i in range(chunk_num):
            left_bound = i * chunk_size
            right_bound = min((i + 1) * chunk_size, len(content))
            tmp_chunk = content[left_bound: right_bound]
            tmp_fcid = md5(tmp_chunk).hexdigest()
            fcid.append(tmp_fcid)
            chunks.append(tmp_chunk[:])
            self.file[fid][tmp_fcid] = tmp_chunk
        # print(len(chunks[0]), len(chunks[1]))
        # print(len(content))
        trans = {"identifier": "REGISTER", "fid": fid, "fcid": fcid, "rate": self.upload_rate}
        msg = pickle.dumps(trans)
        # self.__send__(msg, self.tracker)

        print(len(msg))
        #to judge whether it is successful??
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

        trans = {"identifier": "REGISTER", "fid": fid, "fcid": [fcid], "rate": self.upload_rate}
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
        trans = {"identifier": "QUERY", "fid": fid}
        msg = pickle.dumps(trans)
        self.__send__(msg, self.tracker)
        answer, _ = self.tracker_buffer[fid].get()
        answer = pickle.loads(answer)
        # answer format:
        # {'fcid':[(('ip',port),speed),(('ip1',port1),speed1)],}

        # if download chunk from current fastest source success,we should register this chunk
        chunk_list = answer.keys()
        chunk_queue = SimpleQueue()
        for x in chunk_list:
            chunk_queue.put(x)
        fast = 0
        fast_index = 0
        while not chunk_queue.empty():
            fcid = chunk_queue.get()
            # add fid
            transfer = {"identifier": "QUERY_PEER", "fid": fid, "fcid": fcid}
            for index, x in enumerate(answer[fcid]):
                if x[1] > fast:
                    fast = x[1]
                    fast_index = index
            msg_new = pickle.dumps(transfer)
            self.__send__(msg_new, answer[fcid][fast_index][0])
            message, addr =  self.recv_from_buffer(self.peer_respond_buffer[fcid],3)
            # register the file！
        # if source canceled or closed,we should ask the tracker to update source

        """
        End of your code
        """
        return data

    # def download_chunk(self, fid, fcid):
    #     trans = {"identifier": "GET_CHUNK", "fid": fid, "fcid": [fcid]}
    #     msg = pickle.dumps(trans)
    #     self.__send__(msg, self.tracker)

    def cancel(self, fid):
        """
        Stop sharing a specific file, others should be unable to get this file from this client any more
        :param fid: the unique identification of the file to be canceled register on the Tracker
        :return: You can design as your need
        """

        #TODO: whether to cancel a chunk? Though fid can locate all chunks at the tracker side.
        #TODO: glue all chunks when receiving finishes.
        #TODO: add to my_file after receive.
        #TODO: whether to stop the provice thread? Possibly multiple files shared?
        trans = {"identifier": "CANCEL", "fid": fid}
        msg = pickle.dumps(trans)
        self.__send__(msg, self.tracker)
        # self.provide.join()  #stop the provide thread.

        pass

        """
        End of your code
        """

    def close(self):
        """
        Completely stop the client, this client will be unable to share or download files any more
        :return: You can design as your need
        """
        for file in self.my_file:
            self.cancel(file)
        self.provide.join()
        """
        End of your code
        """
        self.proxy.close()

    def listening(self):
        """
        listening to other PClient's Query,and respond answer
        when self.close() or all the local files are canceled , kill the threading.
        :return:
        """
        while True:
            msg, frm = self.__recv__()
            msg = pickle.loads(msg)
            if msg["identifier"] == "QUERY_RESULT":  # message from tracker
                fid = msg["fid"]
                if fid not in self.tracker_buffer:
                    self.tracker_buffer[fid] = SimpleQueue
                self.tracker_buffer[fid].put((msg, frm))
            elif msg["identifier"] == "QUERY_PEER":  # message from other PClient
                self.peer_query_buffer.put((msg, frm))
            elif msg["identifier"] == "PEER_RESPOND":
                fcid = msg["fcid"]
                if fcid not in self.peer_respond_buffer.keys():
                    self.peer_respond_buffer[fcid] = SimpleQueue()
                self.peer_respond_buffer[fcid].put((msg, frm))

    def recv_from_buffer(self, buffer, timeout=None) -> (
    bytes, (str, int)):  # choose one buffer from three to get a top message
        t = time.time()
        while not timeout or time.time() - t < timeout:
            if not buffer.empty():
                return buffer.get()
            time.sleep(0.000001)
        raise TimeoutError


    def provide_to_peer(self):
        while not self.peer_query_buffer.empty():
            # transfer = {"identifier": "QUERY_PEER", "fid": fid, "fcid": fcid}
            transfer, frm = self.peer_query_buffer.get()
            fid = transfer["fid"]
            fcid = transfer["fcid"]
            result = self.file[fid][fcid]
            transfer = {"identifier": "PEER_RESPOND", "fid": fid, "fcid": fcid, "result": result}
            msg = pickle.dumps(transfer)
            self.__send__(msg, frm)


if __name__ == '__main__':
    tracker_address = ("127.0.0.1", 10086)
    B = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    C = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    id = B.register("./test_files/alice.txt")
    # id1 = C.register("./test_files/alice.txt")
    # msg, frm = B.__recv__()
    # msg1, frm1 = C.__recv__()
    # print(msg, frm)
    # print(msg1, frm1)
    # time.sleep(3)
    # B.register_chunk(id, "testtest123456")
    # msg, frm = B.__recv__()
    # print(msg, frm)
    # files = B.download(id)
    # pass


# TODO: 1. random chunks, 2. 不发也回报文 3. tit for tat   3. 速率变化发给tracker  4. 如果只有A有，连续请求，一定概率接收。
# TODO: Sefl-adaptive intellegent  chunks size