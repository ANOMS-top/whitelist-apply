from rcon import MCRcon
from flask import Flask, render_template, request, make_response, redirect
import csv, hashlib, time


# 配置
ip = '127.0.0.1'    # 服务器RCON的IP
port = 25575        # 服务器RCON的端口
usemd5 = True       # 服务器RCON密码是否为MD5加密过的
webhost = '0.0.0.0' # 审核网站的IP
webport = 8080      # 审核网站的端口

# 一些函数
# RCON远程命令
def serverCommand(pwd, command):
    if usemd5:
        pwd = genmd5(pwd)
    mcr = MCRcon(ip, pwd, port)
    outp = mcr.connect()
    if outp == "Login failed":
        return None
    elif outp == "Connection refused":
        return None
    cmd = mcr.command(command)
    mcr.disconnect()
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

# 读取待审核玩家转成html
def waitlistPendingToHTML(pwd):
    waitlist = readWaitlist()
    pendingList = []
    html = ""
    for i in waitlist:
        if i[3] == "pending":
            pendingList.append(i)
    for i in range(len(pendingList)):
        html += '<tr>\n<th>' + str(i + 1) + '</th>\n<td>' + pendingList[i][0] + '</td>\n<td>' + pendingList[i][1] + '</td>\n<td>' + pendingList[i][2] + '</td>\n<td>待审核</td>\n<td class="table-action">\n<form action="/manage" method="GET">\n<input type="hidden" name="mode" value="accept">\n<input type="hidden" name="pwd" value="' + pwd + '">\n<input type="hidden" name="player" value="' + pendingList[i][0] + '">\n<button type="submit" style="background-color: #4da3f8;">通过</button>\n</form>\n<form action="/manage" method="GET">\n<input type="hidden" name="mode" value="decline">\n<input type="hidden" name="pwd" value="' + pwd + '">\n<input type="hidden" name="player" value="' + pendingList[i][0] + '">\n<button type="submit" style="background-color: #f84d4d;">不通过</button>\n</form>\n</td>\n</tr>'
    return html

# 测试RCON连接
def rconConnect(pwd):
    if usemd5:
        pwd = genmd5(pwd)
    mcr = MCRcon(ip, pwd, port)
    outp = mcr.connect()
    if outp == "Login failed" or outp == "Connection refused":
        return False
    mcr.disconnect()
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
def decline(player):
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
        return render_template('index.html')

# 管理员登录页面
@app.route('/login')
def login():
    # Cookie
    resp = make_response("200")
    pwd = request.cookies.get("pwd")
    if pwd != None:
        if rconConnect(pwd):
            resp.set_cookie("pwd", pwd, max_age = 604800)
            return redirect("/manage")

    return render_template('login.html')

# 登录页面
@app.route('/login/submit', methods=['POST'])
def loginSubmit():
    resp = make_response('<script>window.location.replace("/manage")</script>')
    pwd = request.cookies.get("pwd")
    if pwd != None:
        pwd = request.values.get("pwd")
    else:
        pwd = request.values.get("pwd")
    loginSuccess = rconConnect(pwd)
    if loginSuccess:
        if request.values.get("useCookie") == "on":
            resp.set_cookie("pwd", pwd, max_age = 604800)
            return resp
        else:
            resp.set_cookie("pwd", pwd)
            return resp
    else:
        return render_template('login.html', JS="setTimeout(\"window.alert('登录失败！');\", 10);")

# 待审核管理页面
@app.route('/manage')
def managePending():
    pwd = request.cookies.get("pwd")
    mode = request.args.get("mode")
    player = request.args.get("player")

    loginSuccess = rconConnect(pwd)
    if not loginSuccess:
        return render_template('login.html', JS="setTimeout(\"window.alert('登录失败！');\", 10);")

    if mode == "accept":
        accept(player, pwd)
    if mode == "decline":
        decline(player)
    return render_template('pending.html', table=waitlistPendingToHTML(pwd), pwd=request.values.get("pwd"))

# 玩家状态查询
@app.route('/status')
def statusSearch():
    player = request.args.get("player")
    if player != None:
        waitlist = readWaitlist()
        for i in waitlist:
            if i[0] == player:
                if i[3] == "accepted":
                    status = "已通过"
                elif i[3] == "declined":
                    status = "未通过"
                elif i[3] == "pending":
                    status = "未审核"
                return render_template("status.html", JS="setTimeout(\"window.alert('玩家名称：" + i[0] + "\\\\nQQ号：" + i[1] + "\\\\n申请时间：" + i[2] + "\\\\n申请状态：" + status + "');\", 10);")
        return render_template("status.html", JS="setTimeout(\"window.alert('未在审核列表中找到该玩家！');\", 10);")
    return render_template("status.html")


# 运行Flask
app.run(host=webhost, port=webport, debug=True)
