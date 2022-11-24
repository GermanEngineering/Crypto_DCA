import xml.etree.ElementTree as ET
import logging
from Crypto.Cipher import AES
#from Crypto import Random
#from secrets import token_bytes


_key = b'ENCRYPTION_KEY'
_iv = b'ENCRYPTION_IV'


def GetSettings():
    """Read Settings.xml file."""
    tree = ET.parse("Settings.xml")
    settings = tree.getroot()

    return settings


def GetLogger(filename):
    """Create new logger."""
    logger = logging.getLogger(filename)
    logger.setLevel(logging.DEBUG)
    fileHandler = logging.FileHandler(filename=f"{filename}.log")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(filename)s %(message)s")
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)

    return logger


# https://pycryptodome.readthedocs.io/en/latest/src/examples.html
def Encrypt(public, private):
    # _key = token_bytes(16)
    # _iv = Random.new().read(AES.block_size)

    string1 = f"{public},{private}"
    while len(string1) % 16 != 0:
        string1 += " "

    cipher = AES.new(_key, AES.MODE_EAX, _iv)
    ciphertext = cipher.encrypt(string1.encode("utf-8"))

    return ciphertext


def Decrypt(fileName):
    with open(fileName, "rb") as file:
        ciphertext = file.read()

    cipher = AES.new(_key, AES.MODE_EAX, _iv)
    clearText = cipher.decrypt(ciphertext)

    clearTextString = clearText.decode("utf-8").rstrip()
    public = clearTextString.split(",")[0]
    private = clearTextString.split(",")[1]

    return public, private


def CreateApiKeys(fileName):
    print("Please enter public key:")
    public = input()
    print("Please enter private key:")
    private = input()
    ciphertext = Encrypt(public, private)

    with open(fileName, "wb") as file:
        file.write(ciphertext)

    publicDecrypted, privateDecrypted = Decrypt(fileName)

    #print(public)
    #print(publicDecrypted)
    print(f"Public key encryption successfull - {public == publicDecrypted}")

    #print(private)
    #print(privateDecrypted)
    print(f"Private key encryption successfull - {private == privateDecrypted}")
