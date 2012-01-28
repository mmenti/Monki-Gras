if (navigator.geolocation) {

  var timeoutVal = 10 * 1000 * 1000;
  navigator.geolocation.getCurrentPosition(
    storePosition, 
    handleError,
    { enableHighAccuracy: true, timeout: timeoutVal, maximumAge: 0 }
  );
}
else {
  alert("Geolocation is not supported by this browser");
}

function storePosition(position) {
  $.cookie("posLat", position.coords.latitude);
  $.cookie("posLon", position.coords.longitude);
  $.cookie("posAccuracy", position.coords.accuracy);
  window.location.href = '/start';

}

function handleError(error) {
  var errors = { 
    1: 'Permission denied',
    2: 'Position unavailable',
    3: 'Request timeout'
  };
  alert("Error: " + errors[error.code]);
}
