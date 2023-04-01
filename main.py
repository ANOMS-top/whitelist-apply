from rcon import MCRcon
from flask import Flask, render_template, request
import csv, hashlib, time

# 配置
ip = '127.0.0.1'  # 服务器RCON的IP
port = 25575      # 服务器RCON的端口
usemd5 = True        # 服务器RCON密码是否为MD5加密过的

# 一些函数
# RCON远程命令
def serverCommand(pwd, command):
    print("[RCON] Connecting to" + ip + ":" + str(port))
    if usemd5:
        print("[RCON] Plain password: " + pwd)
        pwd = genmd5(pwd)
        print("[RCON] MD5 Password: " + pwd)
    else:
        print("[RCON] Password: " + pwd)
    mcr = MCRcon(ip, pwd, port)
    if mcr.connect() == "Login failed":
        print("[RCON] Login failed!")
    print("[RCON] Login success!")
    cmd = mcr.command(command)
    print("[RCON] Excuted command: " + command)
    print("[RCON] Command output: " + cmd)
    mcr.disconnect()
    print("[RCON] Disconnected")
    return cmd

# MD5加密
def genmd5(str):
    hl = hashlib.md5()
    hl.update(str.encode(encoding='utf-8'))
    return hl.hexdigest()

# 读取waitlist.csv
def readWaitlist():
    waitlistFile = open("waitlist.csv", "r", newline="")
    waitlist = []
    reader = csv.reader(waitlistFile)
    for row in reader:
        waitlist.append([row[0], row[1], row[2], row[3]])
    waitlistFile.close()
    return waitlist
    
# 写入waitlist.csv
def addWaitlist(player, qq):
    waitlistFile = open("waitlist.csv", "a+", newline="")
    waitlist = readWaitlist()
    for i in waitlist:
        if i[0] == player:
            return False
    now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    writer = csv.writer(waitlistFile)
    writer.writerow([player, str(qq), now, "pending"])
    waitlistFile.close()
    return True
    

# 读取转成html
def waitlistToHTML(pwd):
    waitlist = readWaitlist()
    pendingList = []
    html = ""
    for i in waitlist:
        if i[3] == "pending":
            pendingList.append(i)
    for i in range(len(pendingList)):
        html += '<tr>\n<th>' + str(i + 1) + '</th>\n<td>' + pendingList[i][0] + '</td>\n<td>' + pendingList[i][1] + '</td>\n<td>' + pendingList[i][2] + '</td>\n<td class="table-action">\n<form action="./manage" method="POST">\n<input type="hidden" name="mode" value="accept">\n<input type="hidden" name="pwd" value="' + pwd + '">\n<input type="hidden" name="player" value="' + pendingList[i][0] + '">\n<button type="submit" style="background-color: #4da3f8;">通过</button>\n</form>\n<form action="./manage" method="POST">\n<input type="hidden" name="mode" value="decline">\n<input type="hidden" name="pwd" value="' + pwd + '">\n<input type="hidden" name="player" value="' + pendingList[i][0] + '">\n<button type="submit" style="background-color: #f84d4d;">不通过</button>\n</form>\n</td>\n</tr>'
    return html


# 测试RCON连接
def rconConnect(pwd):
    print("[RCON] Connecting to" + ip + ":" + str(port))
    if usemd5:
        print("[RCON] Plain password: " + pwd)
        pwd = genmd5(pwd)
        print("[RCON] MD5 Password: " + pwd)
    else:
        print("[RCON] Password: " + pwd)
    mcr = MCRcon(ip, pwd, port)
    if mcr.connect() == "Login failed":
        print("[RCON] Login failed!")
        return False
    print("[RCON] Login success!")
    mcr.disconnect()
    print("[RCON] Disconnected")
    return True

# 通过审核
def accept(player, pwd):
    waitlist = readWaitlist()
    for i in range(len(waitlist)):
        if waitlist[i][0] == player and waitlist[i][3] == "pending":
            if serverCommand(pwd, "whitelist add " + player) != None:
                serverCommand(pwd, "whitelist reload")
                waitlist[i][3] = "accepted"
                waitlistFile = open("waitlist.csv", "w+", newline="")
                writer = csv.writer(waitlistFile)
                for i in waitlist:
                    writer.writerow(i)
                
# 不通过审核
def decline(player, pwd):
    waitlist = readWaitlist()
    for i in range(len(waitlist)):
        if waitlist[i][0] == player and waitlist[i][3] == "pending":
            waitlist[i][3] = "declined"
            waitlistFile = open("waitlist.csv", "w+", newline="")
            writer = csv.writer(waitlistFile)
            for i in waitlist:
                writer.writerow(i)

# 初始化
app = Flask(__name__)

# 页面
# 主页
@app.route('/')
def index():
    return render_template('index.html')

# 提交Form页面
@app.route('/submit', methods=['POST'])
def submit():
    if addWaitlist(request.values.get("id"), request.values.get("qq")):
        return render_template('success.html')
    else:
        return render_template('index.html', JS = "setTimeout(\"window.alert('申请失败！');\", 10);")

# 管理员登录页面
@app.route('/login')
def login():
    return render_template('login.html', JS = "")

# 审核管理页面
@app.route('/manage', methods=['POST'])
def manage():
    if not rconConnect(request.values.get("pwd")):
        return render_template('login.html', JS = "setTimeout(\"window.alert('连接失败！');\", 10);")
    if request.values.get("mode") == "accept":
        accept(request.values.get("player"), request.values.get("pwd"))
    if request.values.get("mode") == "decline":
        decline(request.values.get("player"), request.values.get("pwd"))
    return render_template('manage.html', table = waitlistToHTML(request.values.get("pwd")), pwd = request.values.get("pwd"))
    

# 运行Flask
app.run(host="0.0.0.0", port=8080)