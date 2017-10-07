var map;
var service;
var infowindow;

function initializePlaces() {
    // var gmapsLatLngLatestMarkerCoords = new google.maps.LatLng(latestMarker.coords);

    //   map = new google.maps.Map(document.getElementById('map'), {
    //       center: gmapsLatLngLatestMarkerCoords,
    //       zoom: 15
    //     });

    var request = {
        location: latestMarker.coords,
        radius: '50000',
        type: [searchType]
    };
    WriteToHTML('output','Search type: '+searchType+' Search coords: '+latestMarker.coords);
    service = new google.maps.places.PlacesService(map);
    service.nearbySearch(request, PlacesCallback);
    
}

function PlacesCallback(results, status) {
    var stringOutput='Results: ';
    if (status == google.maps.places.PlacesServiceStatus.OK) {
        for (var i = 0; i < results.length; i++) {
            var place = results[i];
            stringOutput+=place.name+', ';
            stringOutput+=place.formatted_address +', ';
            stringOutput+=place.formatted_phone_number +', ';
            //createMarker(results[i]);
    }
    WriteToHTML('output_PLACES', stringOutput );
  }
}

function GetAPIKey(){
    return 'AIzaSyASDYuvialF6b8cR5HCUq6MsFuxxckw3og';
}