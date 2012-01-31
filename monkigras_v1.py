#!/usr/bin/python 

import tornado.ioloop
import tornado.web
import tornado.httpclient
import datetime
import string
import time
import os
import functools
import logging
import urllib


foursq_client_id = YOUR_FOURSQUARE_CLIENT_ID
foursq_client_secret = YOUR_FOURSQUARE_CLIENT_SECRET
untappd_api_key = YOUR_UNTAPPD_API_KEY
bitly_login = YOUR_BITLY_LOGIN
bitly_api_key = YOUR_BITLY_API_KEY

from tornado.options import define, options
define("port", default=8888, help="run on the given port", type=int)

_http_client = None

def _get_http_client():
  global _http_client
  if not _http_client:
    max_simultaneous_connections = 100
    _http_client = tornado.httpclient.AsyncHTTPClient(max_simultaneous_connections=max_simultaneous_connections,
      max_clients=100)
  return _http_client


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
        self.render("detail_notfound.html", title="venue detail")
      else:
        try:
          json = tornado.escape.json_decode(response.body)
          if json["results"]["untappd_venue_id"]:
            http2 = tornado.httpclient.AsyncHTTPClient()
            # get venue feed
            http2.fetch("http://api.untappd.com/v3/venue_checkins?key="+untappd_api_key+"&venue_id="+json["results"]["untappd_venue_id"], callback=self.on_untappd_response)
        except:
          self.render("detail_notfound.html", title="venue detail")

    def on_untappd_response(self, response):
      if response.error:
        # todo: error handling
        raise tornado.web.HTTPError(500)
      else:
        json = tornado.escape.json_decode(response.body)
        self.render("detail.html", title="venue detail", lat=json["results"][0]["venue_lat"], lon=json["results"][0]["venue_lng"], venue_data=json["results"])
        

class BeerHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, beer_id):
      http = tornado.httpclient.AsyncHTTPClient()
      http.fetch("http://api.untappd.com/v3/beer_info?key="+untappd_api_key+"&bid="+beer_id, callback=self.on_response)

    def on_response(self, response):
      global beer_info
      if response.error:
        # todo: error handling
        raise tornado.web.HTTPError(500)
      else:
        json = tornado.escape.json_decode(response.body)
        beer_info = json["results"]
        if json["results"]["brewery_id"] is not None:
          http2 = tornado.httpclient.AsyncHTTPClient()
          # get brewery info
          http2.fetch("http://api.untappd.com/v3/brewery_info?key="+untappd_api_key+"&brewery_id="+json["results"]["brewery_id"], callback=self.on_brewery_response)

    def on_brewery_response(self, response):
      if response.error:
        # todo: error handling
        raise tornado.web.HTTPError(500)
      else:
        json = tornado.escape.json_decode(response.body)
        self.render("beer.html", title="beer detail", beer_data=beer_info, brewery_data=json["results"])

class PufferHandler(tornado.web.RequestHandler):
    @tornado.web.asynchronous
    def get(self, beer_name):
      beername = beer_name
      breweryname = self.get_argument("brewery", None)
      http = tornado.httpclient.AsyncHTTPClient()
      bitly_qstr = "http://api.bitly.com/beta/search?%s" % urllib.urlencode(dict(login=bitly_login, apiKey=bitly_api_key, query="+(!\"%s\" !\"%s\") +(!beer !ale)" % (beername, breweryname)))
      req = tornado.httpclient.HTTPRequest(url=bitly_qstr,
                    method="GET",
                    follow_redirects=False,
                    connect_timeout=20,
                    request_timeout=20,
                    user_agent="brew.lv")
      http.fetch(req, callback=functools.partial(self.on_response, beername=beername))

    def on_response(self, response, beername):
      if response.error:
        # todo: error handling
        raise response.error
      else:
        json = tornado.escape.json_decode(response.body)
        err_msg = ""
        if json["data"]["search"]["numResults"] == 0:
          err_msg = "Sadly we found no bitly search results for " + beername
          self.render("puffer.html", title="bitly results", err_msg=err_msg)
        else:
          self.render("puffer.html", title="bitly results", err_msg=err_msg, results=json["data"]["results"], search_title="bitly results for " + beername)


settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
}

application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/start", StartHandler),
    (r"/pub/(.*)", UntappdHandler),
    (r"/beer/(.*)", BeerHandler),
    (r"/puffer/(.*)", PufferHandler),
], **settings)

if __name__ == "__main__":
    tornado.options.parse_command_line()
    application.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()
