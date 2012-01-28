#!/usr/bin/python 

import tornado.ioloop
import tornado.web
import tornado.httpclient
import datetime
import string
import time
import os

foursq_client_id = "2DQL0QOW0IIZKE4EBGVKII4TW1BFZGDXSF3YOKTSMMNLEVJ4"
foursq_client_secret = "U104NTFKQXSHKZK24Y0O1JQXDXWCWQMP5DGW21J551B5WJCR"
untappd_api_key = "074015fc7c38124a7fda0382b7e1cf18"

from tornado.options import define, options
define("port", default=8888, help="run on the given port", type=int)

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("getloc.html", title="Get current location")

class StartHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self):
      global my_lat
      global my_lon
      global my_acc
      my_lat = self.get_cookie("posLat")
      my_lon = self.get_cookie("posLon")
      my_acc = self.get_cookie("posAccuracy")

      # for demo purposes, override the actual location if lat/lon given in querystring
      override_lat = self.get_argument("lat", None)
      override_lon = self.get_argument("lon", None)

      if override_lat is not None:
        my_lat = override_lat
      if override_lon is not None:
        my_lon = override_lon

      # get 4sq venues nearby
      http = tornado.httpclient.AsyncHTTPClient()
      today = datetime.date.today()
      str_date = today.strftime("%Y%m%d")
      # some 4sq categories (don't think we can make a single request with multiple category ids?)
      # 4bf58dd8d48988d1e5931735  music venue
      # 4d4b7105d754a06374d81259  food
      # 4d4b7105d754a06376d81259  nightlife spot
      http.fetch("https://api.foursquare.com/v2/venues/search?ll="+my_lat+","+my_lon+"&client_id="+foursq_client_id+"&client_secret="+foursq_client_secret+"&v="+str_date+"&categoryId=4d4b7105d754a06376d81259&radius=2000",
                   callback=self.on_response)

    def on_response(self, response):
        if response.error:
          # todo: error handling
          raise tornado.web.HTTPError(500)
        else:
          json = tornado.escape.json_decode(response.body)
          utpd_venue_ids = []
          utpd_venue_names = []
          # for venue in json["response"]["venues"]:
            # look up untappd venue id from 4sq id
            # needs to be blocking?
            # try:
            #   blocking_http_client = tornado.httpclient.HTTPClient()
            #   api_resp = blocking_http_client.fetch("http://api.untappd.com/v3/foursquare_lookup?key="+untappd_api_key+"&vid="+venue["id"])
            #   api_json = tornado.escape.json_decode(api_resp.body)
            #   for api_res in api_json["results"]:
            #     utpd_venue_ids.append(api_res)
            #     # utpd_venue_ids.append(api_res.untappd_venue_id)
            #     # utpd_venue_names.append(api_res.venue_name)
            # except tornado.httpclient.HTTPError, e:
            #   # todo: error handling
            #   pass
          self.render("start.html", title="start", lat=my_lat, lon=my_lon, acc=my_acc, venues=json["response"]["venues"])

    def on_untappd_response(self, response):
        if response.error:
          # todo: error handling
          raise tornado.web.HTTPError(500)
        else:
          json = tornado.escape.json_decode(response.body)

class UntappdHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, fsq_id):
      http = tornado.httpclient.AsyncHTTPClient()
      http.fetch("http://api.untappd.com/v3/foursquare_lookup?key="+untappd_api_key+"&vid="+fsq_id, callback=self.on_response)

    def on_response(self, response):
      if response.error:
        # todo: error handling
        raise tornado.web.HTTPError(500)
      else:
        json = tornado.escape.json_decode(response.body)
        if json["results"]["untappd_venue_id"] is not None:
          http2 = tornado.httpclient.AsyncHTTPClient()
          # get venue feed
          http2.fetch("http://api.untappd.com/v3/venue_checkins?key="+untappd_api_key+"&venue_id="+json["results"]["untappd_venue_id"], callback=self.on_untappd_response)

    def on_untappd_response(self, response):
      if response.error:
        # todo: error handling
        raise tornado.web.HTTPError(500)
      else:
        json = tornado.escape.json_decode(response.body)
        self.render("detail.html", title="venue detail", lat=my_lat, lon=my_lon, acc=my_acc, data=json["results"])
        

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
}

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/start", StartHandler),
    (r"/untpd/(.*)", UntappdHandler),
], **settings)

if __name__ == "__main__":
    tornado.options.parse_command_line()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
