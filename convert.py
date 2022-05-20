from json import dump, load

with open('hat.json', 'r') as inFile:
    hat = load(inFile)

new_hat = {}

for guild in hat:
    new_hat[guild] = {}
    new_hat[guild]['hats'] = {}
    for element in hat[guild]:
        new_hat[guild]['hats'][element] = hat[guild][element]
    new_hat[guild]['filters'] = {}

with open('hat.json', 'w') as outFile:
    dump(new_hat, outFile, indent=2)
