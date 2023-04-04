import socket, ssl, select, struct, time


class MCRconException(Exception):
    pass


class MCRcon(object):
    socket = None

    # 重写init方法
    def __init__(self, host, password, port, tlsmode=0):
        self.host = host
        self.password = password
        self.port = port
        self.tlsmode = tlsmode

    def __exit__(self, type, value, tb):
        self.disconnect()

    def __enter__(self):
        self.connect()
        return self

    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # 打开 TLS
        if self.tlsmode > 0:
            ctx = ssl.create_default_context()

            # 禁用主机名和证书验证
            if self.tlsmode > 1:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            self.socket = ctx.wrap_socket(self.socket, server_hostname=self.host)
        try:
            self.socket.connect((self.host, self.port))
            return self._send(3, self.password)
        except:
            return "Connection refused"

    def _read(self, length):
        data = b""
        while len(data) < length:
            data += self.socket.recv(length - len(data))
        return data

    def disconnect(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None

    def _send(self, out_type, out_data):
        if self.socket is None:
            return ("Not connected")

        # 发送请求包
        out_payload = struct.pack('<ii', 0, out_type) + out_data.encode('utf8') + b'\x00\x00'
        out_length = struct.pack('<i', len(out_payload))
        self.socket.send(out_length + out_payload)

        # 读取响应包
        in_data = ""
        while True:
            # 读取数据包
            in_length, = struct.unpack('<i', self._read(4))
            in_payload = self._read(in_length)
            in_id, in_type = struct.unpack('<ii', in_payload[:8])
            in_data_partial, in_padding = in_payload[8:-2], in_payload[-2:]

            # 异常处理
            if in_padding != b'\x00\x00':
                return ("Incorrect padding")
            if in_id == -1:
                return ("Login failed")

            in_data += in_data_partial.decode('utf8')

            if len(select.select([self.socket], [], [], 0)[0]) == 0:
                return in_data

    def command(self, command):
        result = self._send(2, command)
        time.sleep(0.003)  # MC-72390 （非线程安全的解决办法）
        return result
