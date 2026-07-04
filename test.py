from services.youtube import download_audio

url = "https://youtu.be/JqaAsWRZiEA?si=8HGbT8JjxLV9VVY9"

filename, title = download_audio(url)

print("Название:", title)
print("Файл:", filename)