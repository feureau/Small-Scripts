var map;
var service;
var infowindow;

var addressHolder;
var phoneNumberHolder;

var finalOutputString;

function initializePlaces() {
    // var gmapsLatLngLatestMarkerCoords = new google.maps.LatLng(latestMarker.coords);

    //   map = new google.maps.Map(document.getElementById('map'), {
    //       center: gmapsLatLngLatestMarkerCoords,
    //       zoom: 15
    //     });

    var request = {
        location: latestMarker.coords,
        radius: '500',
        type: [searchType],
        keyword: [searchKeyword]
    };
    // WriteToHTML('output','Search type: '+searchType+' Search coords: '+latestMarker.coords);
    service = new google.maps.places.PlacesService(map);
    service.nearbySearch(request, PlacesCallback);
    
}

function PlacesCallback(results, status) {
    finalOutputString='';
    var stringOutput='Results: ';
    if (status == google.maps.places.PlacesServiceStatus.OK) {
        for (var i = 0; i < results.length; i++) {
            var place = results[i];
            finalOutputString+=place.name + ', ';
            finalOutputString+=place.place_id + ', ';
            var requestForGetDetails = {
                placeId: place.place_id
              };
            service.getDetails(requestForGetDetails, GetDetailsCallback);
            
            finalOutputString+='<br>';  
            //createMarker(results[i]);
    }
    //wait(10000);
    WriteToHTML('output_PLACES', finalOutputString );
  }
}

function GetDetailsCallback(place, status) {
    if (status == google.maps.places.PlacesServiceStatus.OK) {
        finalOutputString+=place.formatted_address + ', ';
        finalOutputString+=place.formatted_phone_number + ', ';
    }
    
  }

function GetAPIKey(){
    return 'AIzaSyASDYuvialF6b8cR5HCUq6MsFuxxckw3og';
}

function wait(ms){
    var start = new Date().getTime();
    var end = start;
    while(end < start + ms) {
      end = new Date().getTime();
   }
 }