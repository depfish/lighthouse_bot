FROM python:3.8-alpine
WORKDIR /app

RUN apk --no-cache add vim tzdata build-base
ADD ./ /app
RUN pip install -r requirements.pip
RUN (crontab -l ; echo "*/5	* *	* *	/usr/local/bin/python3 /app/main.py") | crontab -

CMD ["crond", "-f"]
