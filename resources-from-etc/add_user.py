import json

def add_attributes():
    with open("image_responses.json", "r+") as response_file:
        responses = json.load(response_file)
    new_response = {}
    for call, response in responses.items():
        new_response[call] = {}
        new_response[call]["response"] = response
        new_response[call]["user"] = "Roscroft"
    with open("new_responses.json", "w") as response_file:
        json.dump(new_response, response_file)

add_attributes()
