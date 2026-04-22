from sila2.client import SilaClient

client = SilaClient("192.168.10.2", 50053, insecure=True)
for val in client.DMMController.Resistance.subscribe():
    print(val)