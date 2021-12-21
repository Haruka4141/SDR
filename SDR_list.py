import subprocess

def raw_command(IP, raw):
    cmd = "ipmitool -I lanplus -H " + IP + " -U admin -P admin raw " + raw
    # print(cmd)
    process = subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE)
    #                                ^ if passing a single string, either shell must be True or else the string is not having argument                                        
    output = process.stdout
    output = output.read()
    #print(type(repo))
    #print(repo)         #byte string

    output = output.strip().decode(encoding = "UTF-8")    #string
    # print(type(repo))
    # print(repo + "\n")

    output_list = output.split()

    return output_list

def full_sensor_ID(sdr):
    ID = ""
    for index in range(50, len(sdr)):
        ID += chr(int(sdr[index], 16))
    return ID

def compact_sensor_ID(sdr):
    ID = ""
    for index in range(34, len(sdr)):
        ID += chr(int(sdr[index], 16))
    return ID


# analog reading should be converted by SDR factors
def sensor_reading(IP, sdr):
    response = raw_command(IP, "0x4 0x2d 0x" + sdr[9])
    # print(response)

    converted_reading = analog_convert(sdr, response[0])
    converted_reading += " " + get_unit(sdr) 
    
    status = get_status(response, sdr)
    if status == "state unavaliable":
        converted_reading = "no reading"

    return [converted_reading, status]

def analog_convert(sdr, reading):

    x = int(reading, 16)
    factor_list = sdr_factor(sdr)

    multi = factor_list[0]
    add = factor_list[1]
    R_exp = factor_list[2]
    B_exp = factor_list[3]

    Y = (multi * x + (add * 10 ** B_exp)) * 10 ** R_exp     # exponentiaiton operator is **, not ^
    return "{:5.2f}".format(Y)

def get_unit(sdr):
    
    sensor_unit_1 = int(sdr[22],16)
    sensor_unit_2 = int(sdr[23],16)
    sensor_unit_3 = int(sdr[24],16)
    
    unit = {
        0:'unspecified', 
        1:'degrees C',
        2:'degrees F',
        3:'degrees K',
        4:'Volts',
        5:'Amps',
        6:'Watts',
        7:'Joules',
        8:'Coulombs',
        9:'VA',
        10:'Nits',
        11:'lumen',
        12:'lux',
        13:'Candela',
        14:'kPa',
        15:'PSI',
        16:'Newton',
        17:'CFM',
        18:'RPM',
        19:'Hz',
        20:'microsecond',
        21:'millisecond',
        22:'second',
        23:'minute',
        24:'hour',
        25:'day',
        26:'week'
    }
    return unit.get(sensor_unit_2)

# theshold sensor
def get_status(response, sdr):
    
    if int(response[1], 16) & 32 != 0:
        return "state unavaliable"

    theshold_status = {
        0:"ok",
        1:"<= lower non-critical",
        2:"<= lower critical",
        4:"<= lower non-recoverable",
        8:">= upper non-critical",
        16:">= upper critical",
        32:">= upper non-recoverable"
    }

    discrete_status_1 = {        
        1:"state 0 asserted",
        2:"state 1 asserted",
        4:"state 2 asserted",
        8:"state 3 asserted",
        16:"state 4 asserted",
        32:"state 5 asserted",
        64:"state 6 asserted",
        128:"state 7 asserted"
    }

    discrete_status_2 = {
        1:"state 8 asserted",
        2:"state 9 asserted",
        4:"state 10 asserted",
        8:"state 11 asserted",
        16:"state 12 asserted",
        32:"state 13 asserted",
        64:"state 14 asserted"
    }

    if sdr[5] == "01":
        status = int(response[2], 16) & 63
        return theshold_status.get(status)
    if sdr[5] == "02":
        if response[2] != "00":
            status = int(response[2], 16) & 255
            return discrete_status_1.get(status)
        elif response[3] != "80":
            status = int(response[3], 16) & 127
            return discrete_status_2.get(status)
        else:
            return "ok"

# nominal_reading in SDR is not sensor return value, using Get Sensor Reading to get sensor value
# Tolerance & Accuracy are not used
def sdr_factor(sdr):

    M = int(sdr[26], 16)
    M_T = int(sdr[27], 16)
    B = int(sdr[28], 16)
    B_A = int(sdr[29], 16)
    R_B = int(sdr[31], 16)
    x = int(sdr[33], 16)

    multi = M + ((M_T >> 6) << 8)
    add = B + ((B_A >> 6) << 8)

    if R_B >> 7 == 1:
        R_exp = -(8 - (R_B >> 4) & 7)
    else:
        R_exp = R_B >> 4
    
    if (R_B >> 3) & 1 == 1:
        B_exp = -(8 - R_B & 7)
    else:
        B_exp = R_B & 7
    
    factor_list = [multi, add, R_exp, B_exp]

    return factor_list

# same as ipmitool sdr list
def sensor_print(ID, reading):
    print("{:14} | {:<20} | {:20}".format(ID, reading[0], reading[1]))

def main():
    IP = input("Enter IP: ")
    repo = raw_command(IP, "0xa 0x22")              # get repository only once!
    repo = "0x" + repo[0] + " " + "0x" + repo[1]
    cmd = "0xa 0x23 " + repo + " 0x0 0x0 0x0 0xff"

    sdr = raw_command(IP, cmd)
    while sdr[0] != "ff" and sdr[1] != "ff":        # FFFFh specifies that the last SDR should be listed
        if sdr[5] == "01":                          # get full sensor
            ID = full_sensor_ID(sdr)
            reading = sensor_reading(IP, sdr)
            sensor_print(ID, reading)
        if sdr[5] == "02":                          # get compact sensor
            ID = compact_sensor_ID(sdr)
            reading = sensor_reading(IP, sdr)
            sensor_print(ID, reading)
        
            
        cmd = "0xa 0x23 " + repo + " 0x" + sdr[0] + " 0x" + sdr[1] + " 0x0 0xff"
        sdr = raw_command(IP, cmd)

main()
