from exa_py import Exa

exa = Exa(api_key = "995da727-7b91-42d0-b282-326daa290b39")

response = exa.stream_answer(
    "How close are we to meeting aliens?",
    text=True
)

for chunk in response:
    print(chunk, end='', flush=True)
