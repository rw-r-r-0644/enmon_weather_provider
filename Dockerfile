FROM python:3.11.5-alpine3.18

WORKDIR /usr/src/app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt
CMD [ "python", "./weather_provider.py" ]
