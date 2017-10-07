var map;
var service;
var infowindow;

var addressHolder;
var phoneNumberHolder;

var tempArray;

var finalOutputArray;
var finalOutputString;

function initializePlaces() {
    // var gmapsLatLngLatestMarkerCoords = new google.maps.LatLng(latestMarker.coords);

    //   map = new google.maps.Map(document.getElementById('map'), {
    //       center: gmapsLatLngLatestMarkerCoords,
    //       zoom: 15
    //     });
    finalOutputArray=[];
    finalOutputString='';
    var request = {
        location: latestMarker.coords,
        radius: '50000',
        type: [searchType],
        keyword: [searchKeyword]
    };
    // WriteToHTML('output','Search type: '+searchType+' Search coords: '+latestMarker.coords);
    service = new google.maps.places.PlacesService(map);
    service.nearbySearch(request, PlacesCallback);
    
}

function PlacesCallback(results, status) {
    var stringOutput='Results: ';
    if (status == google.maps.places.PlacesServiceStatus.OK) {
        for (var i = 0; i < results.length; i++) {
            var place = results[i];
 
            var requestForGetDetails = {
                placeId: place.place_id
              };
            service.getDetails(requestForGetDetails, GetDetailsCallback);
            
    }
    //wait(10000);
    WriteToHTML('output_PLACES', finalOutputString );
  }
}

function GetDetailsCallback(place, status) {
    if (status == google.maps.places.PlacesServiceStatus.OK) {
        AppendToFinalOutputString(place.name,true);
        AppendToFinalOutputString(place.formatted_address,true);
        AppendToFinalOutputString(place.formatted_phone_number,true);
        AppendToFinalOutputString(place.website,true);
        AppendToFinalOutputString(place.place_id,true);
        AppendToFinalOutputString('<br>',false);
        WriteToHTML('output_PLACES', finalOutputString );
    }
    
}

function AppendToFinalOutputString(stringToAdd,withComma){
    if (withComma==true){

        finalOutputString+=stringToAdd + ', ';
    }
    else{
        finalOutputString+=stringToAdd;
    }
}


function GetAPIKey(){
    return 'AIzaSyASDYuvialF6b8cR5HCUq6MsFuxxckw3og';
}

