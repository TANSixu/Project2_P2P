import threading
import time
import random
from Proxy import Proxy
from hashlib import md5
import numpy as np
import pickle
from queue import SimpleQueue, PriorityQueue
from threading import Thread
from concurrent.futures import ThreadPoolExecutor


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
        self.priority = []
        self.max_try_download_length = 3
        self.max_accept_length = 1
        self.accept_rate = 0.1
        self.chunk_size = 32 * 1024
        self.active = True
        self.peer = {}
        # 变量定义不可以写在线程start后面
        self.listen = Thread(target=self.listening, args=())
        self.listen.start()
        # self.provide = Thread(target=self.provide_to_peer, args=())  # thread to provide trunk to peer
        # self.provide.start()
        #self.rate_change = Thread(target=self.listen_rate_change, args=())
        #self.rate_change.start()

        # threading pool
        #self.pool = ThreadPoolExecutor(max_workers=10)

        # DEBUG
        self.cnt_pkt = 0

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

    # def listen_rate_change(self):
    #     var = self.upload_rate
    #     while self.active:
    #         if var != self.upload_rate:
    #             trans = {"identifier": "CHANGE_RATE", "rate": self.upload_rate}
    #             msg = pickle.dumps(trans)
    #             self.__send__(msg, self.tracker)
    #             var = self.upload_rate  # update var
    #         else:
    #             time.sleep(1)


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
        trans = {"identifier": "REGISTER", "fid": fid, "fcid": fcid}
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

        trans = {"identifier": "REGISTER", "fid": fid, "fcid": [fcid]}
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
        pool = ThreadPoolExecutor(max_workers=10)
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
            pool.submit(self.download_chunk, fid, fcid, chunk_queue)


        pool.shutdown(wait=True)
        result = []
        for fcid in self.file[fid].keys():
            chunk = self.file[fid][fcid]
            result.append((fcid, chunk))
        result.sort(key=lambda y: int(y[0], 16))
        data = bytes()
        for x in result:
            data = data + x[1]

        return data

    def download_chunk(self, fid, fcid, chunk_queue):
        tran = {"identifier": "QUERY_TRUNK", "fid": fid, "fcid": fcid}
        msg = pickle.dumps(tran)
        self.__send__(msg, self.tracker)
        answer0, _ = self.recv_from_dict(self.tracker_buffer, fcid, 3)
        transfer = {"identifier": "QUERY_PEER", "fid": fid, "fcid": fcid}
        answer = answer0["result"]

        if len(answer) == 0:
            print("Empty record")
            chunk_queue.put(fcid)
            return
        for client in answer:
            if client not in self.peer.keys():
                self.peer[client] = 0
        answer.sort(key=lambda x:self.peer[x])
        fast = answer[0]
        # for i in range(len(answer)):
        #     client = answer[i]
        #     if client in self.peer.keys():
        #         if self.peer[client]<self.peer[fast]:
        #             fast = client
        #     else:
        #         fast = client
        #         break
        #answer.sort(key=lambda x: (x[1], random.random()), reverse=True)
        msg_new = pickle.dumps(transfer)



        self.__send__(msg_new, fast)
        index = 1
        cnt = 0

        while True:
            try:
                message, addr = self.recv_from_dict(self.peer_respond_buffer, fcid, 10)
                if message["state"] == "success":
                    break
                else:
                    if cnt < self.max_try_download_length:
                        transfer = {"identifier": "QUERY_PEER", "fid": fid, "fcid": fcid}
                        msg_new = pickle.dumps(transfer)
                        self.__send__(msg_new, answer[index % len(answer)])
                        index += 1
                        cnt += 1
                    else:
                        cnt = 0
                        index = 1
                        tran = {"identifier": "QUERY_TRUNK", "fid": fid, "fcid": fcid}
                        msg = pickle.dumps(tran)
                        self.__send__(msg, self.tracker)
                        answer1, _ = self.tracker_buffer[fcid].get()
                        transfer = {"identifier": "QUERY_PEER", "fid": fid, "fcid": fcid}
                        answer = answer1["result"]
                        answer.sort(key=lambda y: y[1])
                        msg_new = pickle.dumps(transfer)
                        self.__send__(msg_new, answer[0])
            except TimeoutError:

                transfer = {"identifier": "QUERY_PEER", "fid": fid, "fcid": fcid}
                msg_new = pickle.dumps(transfer)
                self.__send__(msg_new, answer[index % len(answer)][0])
                index += 1

        self.register_chunk(fid, fcid)
        self.file[fid][fcid] = message["result"]



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
        while not self.proxy.send_queue.empty():
            continue
        """
        End of your code
        """
        self.active = False
        self.proxy.close()

        return self.cnt_pkt

    def listening(self):
        """
        listening to other PClient's Query,and respond answer
        when self.close() or all the local files are canceled , kill the threading.
        :return:
        """
        while self.active:

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
                self.provide_to_peer_tit_tat()

            elif msg["identifier"] == "PEER_RESPOND":
                fcid = msg["fcid"]
                if msg["state"]=="success":
                    self.peer[frm] = time.time() - msg["time"]
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
        timeout = None
        t = time.time()
        while not timeout or time.time() - t < timeout:
            if fid in buffer.keys():
                if not buffer[fid].empty():
                    return buffer[fid].get()
            time.sleep(0.0001)
        raise TimeoutError

    def provide_to_peer_tit_tat(self):
        # 在列表中或者列表没满 直接发送并加入列表
        # 不在列表中但是速率超过列表最慢项 加入列表
        # 不在列表中但是速率小于列表最慢项 概率发送 加入列表
        # 发送一个失败的消息回复
        while not self.peer_query_buffer.empty():
            transfer, frm = self.peer_query_buffer.get()
            if frm not in self.peer.keys():
                fid = transfer["fid"]
                fcid = transfer["fcid"]
                result = self.file[fid][fcid]
                transfer = {"identifier": "PEER_RESPOND", "state": "success", "fid": fid, "fcid": fcid,
                            "result": result, "time": time.time()}
                msg = pickle.dumps(transfer)
                self.__send__(msg, frm)
                self.cnt_pkt += 1
            elif len(self.priority) < self.max_accept_length or self.priority.__contains__(frm) :
                if self.proxy.port ==38438:
                    print(self.proxy.port, " ", self.priority)
                    print(self.peer)
                if not self.priority.__contains__(frm):
                    self.priority.append(frm)
                fid = transfer["fid"]
                fcid = transfer["fcid"]
                result = self.file[fid][fcid]
                transfer = {"identifier": "PEER_RESPOND", "state": "success", "fid": fid, "fcid": fcid,
                            "result": result,"time":time.time()}
                msg = pickle.dumps(transfer)
                self.__send__(msg, frm)
                self.cnt_pkt += 1
            else:
                self.priority.sort(key=lambda x:self.peer[x],reverse=True)
                if self.proxy.port == 38438:
                    print(self.proxy.port, " ", self.priority)
                    print(self.peer)
                least_frm = self.priority.pop(0)
                if self.peer[least_frm]>self.peer[frm]:
                    self.priority.append(frm)
                    fid = transfer["fid"]
                    fcid = transfer["fcid"]
                    result = self.file[fid][fcid]
                    transfer = {"identifier": "PEER_RESPOND", "state": "success", "fid": fid, "fcid": fcid,
                                "result": result,"time":time.time()}
                    msg = pickle.dumps(transfer)
                    self.__send__(msg, frm)
                    self.cnt_pkt += 1
                else:
                    rand = random.random()
                    if rand < self.accept_rate:
                        self.priority.append(frm)
                        fid = transfer["fid"]
                        fcid = transfer["fcid"]
                        result = self.file[fid][fcid]
                        transfer = {"identifier": "PEER_RESPOND", "state": "success", "fid": fid, "fcid": fcid,
                                    "result": result,"time":time.time()}
                        msg = pickle.dumps(transfer)
                        self.__send__(msg, frm)
                        self.cnt_pkt += 1
                    else:
                        fid = transfer["fid"]
                        fcid = transfer["fcid"]
                        self.priority.append(least_frm)
                        transfer = {"identifier": "PEER_RESPOND", "state": "fail", "fid": fid, "fcid": fcid,"time":time.time()}
                        msg = pickle.dumps(transfer)
                        self.__send__(msg, frm)

    def provide_to_peer(self):
        while not self.peer_query_buffer.empty():
            transfer, frm = self.peer_query_buffer.get()
            fid = transfer["fid"]
            fcid = transfer["fcid"]
            result = self.file[fid][fcid]

            transfer = {"identifier": "PEER_RESPOND", "state": "success", "fid": fid, "fcid": fcid,
                        "result": result,"time":time.time()}
            msg = pickle.dumps(transfer)
            self.__send__(msg, frm)
            self.cnt_pkt+=1

            # for i in range(4):
            #     left_bound = i * self.chunk_size/4
            #     right_bound = min((i + 1) * self.chunk_size/4, len(result))
            #     tmp_chunk = result[int(left_bound): int(right_bound)]
            #     transfer = {"identifier": "PEER_RESPOND", "state": "success", "fid": fid, "fcid": fcid,"result": tmp_chunk,"index":i}
            #     msg = pickle.dumps(transfer)
            #     self.__send__(msg, frm)


if __name__ == '__main__':
    tracker_address = ("127.0.0.1", 10086)
    B = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    C = PClient(tracker_address, upload_rate=100000, download_rate=100000)
    id = B.register("./test_files/bg.png")
    t = time.time()
    files = C.download(id)
    print("total time = ", time.time() - t)
    C.close()
    B.close()

# TODO: 1. random chunks √
#       2. 不发也回报文  √
#       3. tit for tat √
#       3. 速率变化发给tracker √
#       4. 如果只有A有，连续请求，一定概率接收。√
# TODO: Sefl-adaptive intellegent  chunks size :)
