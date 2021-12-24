import time
import random
from Proxy import Proxy
from hashlib import md5
import numpy as np
import pickle
from queue import SimpleQueue, PriorityQueue
from threading import Thread


class PClient:
    def __init__(self, tracker_addr: (str, int), proxy=None, port=None, upload_rate=0, download_rate=0):
        if proxy:
            self.proxy = proxy
        else:
            self.proxy = Proxy(upload_rate, download_rate, port)  # Do not modify this line!
        self.tracker = tracker_addr
        self.upload_rate = upload_rate
        self.download_rate = download_rate
        self.file = {}  # key: fid, fcid ; values: corresponding bytes
        self.tracker_buffer = {}  # key:fid value:simpleQueue
        self.peer_query_buffer = SimpleQueue()  # message from other PClient (other PClient query you)
        self.peer_respond_buffer = {}  # key = fcid value= simplequeue
        self.priority = PriorityQueue()
        self.max_try_download_length = 3
        self.max_accept_length = 4
        self.accept_rate = 0.3
        self.chunk_size = 32 * 1024
        self.active = True
        # 变量定义不可以写在线程start后面
        self.listen = Thread(target=self.listening, args=())
        self.listen.start()
        # self.provide = Thread(target=self.provide_to_peer, args=())  # thread to provide trunk to peer
        # self.provide.start()
        self.rate_change = Thread(target=self.listen_rate_change, args=())
        self.rate_change.start()

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

    def listen_rate_change(self):
        var = self.upload_rate
        while self.active:
            if var != self.upload_rate:
                trans = {"identifier": "CHANGE_RATE", "rate": self.upload_rate}
                msg = pickle.dumps(trans)
                self.__send__(msg, self.tracker)
                var = self.upload_rate  # update var
            else:
                time.sleep(1)

    def register(self, file_path: str):
        """
        Share a file in P2P network
        :param file_path: The path to be shared, such as "./alice.txt"
        :return: fid, which is a unique identification of the shared file and can be used by other PClients to
                 download this file, such as a hash code of it
        """
        # fid = None
        """
        Start your code below!
        """
        with open(file_path, "rb") as file:
            content = file.read()

        chunk_num = int(np.ceil(len(content) / self.chunk_size))
        fid = md5(content).hexdigest()
        chunks = []
        self.file[fid] = {}
        fcid = []
        for i in range(chunk_num):
            left_bound = i * self.chunk_size
            right_bound = min((i + 1) * self.chunk_size, len(content))
            tmp_chunk = content[left_bound: right_bound]
            tmp_fcid = "{fid}{i}".format(fid=fid, i=i)
            fcid.append(tmp_fcid)
            chunks.append(tmp_chunk[:])
            self.file[fid][tmp_fcid] = tmp_chunk
        trans = {"identifier": "REGISTER", "fid": fid, "fcid": fcid, "rate": self.upload_rate}
        msg = pickle.dumps(trans)
        self.__send__(msg, self.tracker)

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

        while True:
            try:
                self.__send__(msg, self.tracker)
                answer1, _ = self.recv_from_dict(self.tracker_buffer, fid, 3)
                if len(answer1["result"]) > 0:
                    break
            except TimeoutError:
                print("Go back home, we dont have your place!")
        # answer format:
        # {'fcid':[(('ip',port),speed),(('ip1',port1),speed1)],}

        # if download chunk from current fastest source success,we should register this chunk
        chunk_list = answer1["result"]

        # random chunk
        random.shuffle(chunk_list)
        chunk_queue = SimpleQueue()
        if fid not in self.file.keys():
            self.file[fid] = {}
        for i in range(len(chunk_list)):
            chunk_queue.put(chunk_list[i])
        while not chunk_queue.empty():
            fcid = chunk_queue.get()
            # add fid
            tran = {"identifier": "QUERY_TRUNK", "fid": fid, "fcid": fcid}
            msg = pickle.dumps(tran)
            self.__send__(msg, self.tracker)
            answer0, _ = self.recv_from_dict(self.tracker_buffer, fcid, 3)
            transfer = {"identifier": "QUERY_PEER", "fid": fid, "fcid": fcid, "upload_rate": self.upload_rate}
            answer = answer0["result"]
            answer.sort(key=lambda x: (x[1], random.random()), reverse=True)
            msg_new = pickle.dumps(transfer)
            self.__send__(msg_new, answer[0][0])
            index = 1
            cnt = 0
            t=time.time()
            while True:
                try:
                    message, addr = self.recv_from_dict(self.peer_respond_buffer, fcid, 10)
                    print(time.time()-t)
                    print("receive trunk from:", addr)
                    if message["state"] == "success":
                        break
                    else:
                        if cnt < self.max_try_download_length:
                            transfer = {"identifier": "QUERY_PEER", "fid": fid, "fcid": fcid,
                                        "upload_rate": self.upload_rate}
                            msg_new = pickle.dumps(transfer)
                            self.__send__(msg_new, answer[index % len(answer)][0])
                            index += 1
                            cnt += 1
                        else:
                            cnt = 0
                            index = 1
                            tran = {"identifier": "QUERY_TRUNK", "fid": fid, "fcid": fcid}
                            msg = pickle.dumps(tran)
                            self.__send__(msg, self.tracker)
                            answer1, _ = self.tracker_buffer[fcid].get()
                            transfer = {"identifier": "QUERY_PEER", "fid": fid, "fcid": fcid,
                                        "upload_rate": self.upload_rate}
                            answer = answer1["result"]
                            answer.sort(key=lambda y: y[1])
                            msg_new = pickle.dumps(transfer)
                            self.__send__(msg_new, answer[0][0])
                except TimeoutError:

                    transfer = {"identifier": "QUERY_PEER", "fid": fid, "fcid": fcid,
                                "upload_rate": self.upload_rate}
                    msg_new = pickle.dumps(transfer)
                    self.__send__(msg_new, answer[index % len(answer)][0])
                    index += 1
            self.register_chunk(fid, fcid)
            self.file[fid][fcid] = message["result"]

        result = []
        for fcid in self.file[fid].keys():
            chunk = self.file[fid][fcid]
            result.append((fcid, chunk))
        result.sort(key=lambda y: int(y[0], 16))
        data = bytes()
        for x in result:
            data = data + x[1]
        # fo = open("{fid}.txt".format(fid=fid), "wb")
        # fo.write(data)
        # fo.close()

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

        # TODO: whether to cancel a chunk? Though fid can locate all chunks at the tracker side.
        # TODO: whether to stop the provice thread? Possibly multiple files shared?
        trans = {"identifier": "CANCEL", "fid": fid}
        msg = pickle.dumps(trans)
        self.__send__(msg, self.tracker)
        # self.provide.join()  #stop the provide thread.

        # pass

        """
        End of your code
        """

    def close(self):
        """
        Completely stop the client, this client will be unable to share or download files any more
        :return: You can design as your need
        """
        for file in self.file.keys():
            self.cancel(file)
        # self.rate_change.join()
        """
        End of your code
        """
        while not self.proxy.send_queue.empty():
            #time.sleep(0.0001)
            continue
        self.active = False
        self.proxy.close()

    def listening(self):
        """
        listening to other PClient's Query,and respond answer
        when self.close() or all the local files are canceled , kill the threading.
        :return:
        """
        while self.active:
            # if not self.proxy.recv_queue.empty():
            if self.proxy.recv_queue.empty():
                time.sleep(0.0001)
                continue
            msg, frm = self.__recv__()
            msg = pickle.loads(msg)
            if msg["identifier"] == "QUERY_RESULT_INITIAL":  # message from tracker
                fid = msg["fid"]
                if fid not in self.tracker_buffer.keys():
                    self.tracker_buffer[fid] = SimpleQueue()
                self.tracker_buffer[fid].put((msg, frm))
            elif msg["identifier"] == "QUERY_RESULT_EACH":  # message from tracker
                fcid = msg["fcid"]
                if fcid not in self.tracker_buffer.keys():
                    self.tracker_buffer[fcid] = SimpleQueue()
                self.tracker_buffer[fcid].put((msg, frm))
            elif msg["identifier"] == "QUERY_PEER":  # message from other PClient
                self.peer_query_buffer.put((msg, frm))
                self.provide_to_peer()

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
            time.sleep(0.0001)
        raise TimeoutError

    def recv_from_dict(self, buffer, fid, timeout=None):
        t = time.time()
        while not timeout or time.time() - t < timeout:
            if fid in buffer.keys():
                if not buffer[fid].empty():
                    return buffer[fid].get()
                #time.sleep(0.0001)
            time.sleep(0.0001)
        raise TimeoutError

    def provide_to_peer_tit_tat(self):
        # 在列表中或者列表没满 直接发送并加入列表
        # 不在列表中但是速率超过列表最慢项 加入列表
        # 不在列表中但是速率小于列表最慢项 概率发送 加入列表
        # 发送一个失败的消息回复
        while not self.peer_query_buffer.empty():
            # transfer = {"identifier": "QUERY_PEER", "fid": fid, "fcid": fcid, "upload_rate":...}
            transfer, frm = self.peer_query_buffer.get()
            if self.priority.qsize() < self.max_accept_length:
                upload_rate = transfer["upload_rate"]
                self.priority.put([upload_rate, frm])
                fid = transfer["fid"]
                fcid = transfer["fcid"]
                result = self.file[fid][fcid]
                transfer = {"identifier": "PEER_RESPOND", "state": "success", "fid": fid, "fcid": fcid,
                            "result": result}
                msg = pickle.dumps(transfer)
                self.__send__(msg, frm)
            else:
                least_frm = self.priority.get()
                if least_frm[0] < transfer["upload_rate"]:
                    self.priority.put([transfer["upload_rate"], frm])
                    fid = transfer["fid"]
                    fcid = transfer["fcid"]
                    result = self.file[fid][fcid]
                    transfer = {"identifier": "PEER_RESPOND", "state": "success", "fid": fid, "fcid": fcid,
                                "result": result}
                    msg = pickle.dumps(transfer)
                    self.__send__(msg, frm)
                else:
                    rand = random.random()
                    if rand < self.accept_rate:
                        self.priority.put([transfer["upload_rate"], frm])
                        fid = transfer["fid"]
                        fcid = transfer["fcid"]
                        result = self.file[fid][fcid]
                        transfer = {"identifier": "PEER_RESPOND", "state": "success", "fid": fid, "fcid": fcid,
                                    "result": result}
                        msg = pickle.dumps(transfer)
                        self.__send__(msg, frm)
                    else:
                        fid = transfer["fid"]
                        fcid = transfer["fcid"]
                        self.priority.put(least_frm)
                        transfer = {"identifier": "PEER_RESPOND", "state": "fail", "fid": fid, "fcid": fcid}
                        msg = pickle.dumps(transfer)
                        self.__send__(msg, frm)

    def provide_to_peer(self):
        while not self.peer_query_buffer.empty():
            transfer, frm = self.peer_query_buffer.get()
            fid = transfer["fid"]
            fcid = transfer["fcid"]
            result = self.file[fid][fcid]
            transfer = {"identifier": "PEER_RESPOND", "state": "success", "fid": fid, "fcid": fcid,
                        "result": result}
            msg = pickle.dumps(transfer)
            self.__send__(msg, frm)


if __name__ == '__main__':
    tracker_address = ("127.0.0.1", 10086)
    B = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    C = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    id = B.register("./test_files/bg.png")
    # id1 = C.register("./test_files/alice.txt")
    # msg, frm = B.__recv__()
    # msg1, frm1 = C.__recv__()
    # print(msg, frm)
    # print(msg1, frm1)
    # time.sleep(3)
    # B.register_chunk(id, "testtest123456")
    # msg, frm = B.__recv__()
    # print(msg, frm)
    t = time.time()
    files = C.download(id)
    print("total time = ", time.time() - t)
    C.close()
    B.close()
    # pass

# TODO: 1. random chunks √
#       2. 不发也回报文  √
#       3. tit for tat √
#       3. 速率变化发给tracker √
#       4. 如果只有A有，连续请求，一定概率接收。√
# TODO: Sefl-adaptive intellegent  chunks size :)

# question:
# 1. timeout =10
# 2. close the thread
