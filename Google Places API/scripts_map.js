var mainArray=[];
var latestMarker;
var searchKeyword;
var searchType;
var map;

//initialize map. When user clicks on map, adds marker, and add that marker coordinate to mainArray.
function initMap(){
    // Map options
    var options = {
      zoom:8,
      center:{lat:-6.932243417891073,lng:107.63031005859375} 
    }

    // New map
    map = new google.maps.Map(document.getElementById('map'), options);

    // Listen for click on map
    google.maps.event.addListener(map, 'click', function(event){
      // Add marker
      addMarker({coords:event.latLng});
      mainArray.push({coords:event.latLng});
        latestMarker={coords:event.latLng};
      //latestMarker={coords:event.lat,coords:event.lng};
    });

    // Add Marker Function
    function addMarker(props){
        var marker = new google.maps.Marker( { position:props.coords, map:map, } ); //icon:props.iconImage

        // Check for customicon
        if(props.iconImage){ marker.setIcon(props.iconImage); }// Set icon image

        // Check content
        if(props.content){var infoWindow = new google.maps.InfoWindow({content:props.content});
            marker.addListener('click', function(){infoWindow.open(map, marker);});
        }
    }
  }

function WriteToHTML(elementByID, stringToWrite){
    document.getElementById(elementByID).innerHTML = stringToWrite;
}

function LoopThroughArrayAndConvertToString(thisArray){
    var stringToReturn = 'text ';
    for ( i=0; thisArray.length>i; i++ ){
        stringToReturn = stringToReturn + thisArray[i].coords;
    }
    return stringToReturn;
}

function DoSearch(){
    searchType= document.getElementById("type").value;
    searchKeyword= document.getElementById("keyword").value;
    var thingsThatAreEmpty='';
    if (latestMarker==null){
        thingsThatAreEmpty+= 'marker ';
    }
    // if (searchKeyword==''){
    //     if (latestMarker==null){
    //         thingsThatAreEmpty+= 'and keyword ';
    //     }else{
    //         thingsThatAreEmpty+= 'keyword ';
    //     }
    // }

    if(latestMarker==null){
        WriteToHTML('output','You forgot to add a '+ thingsThatAreEmpty+'on the map.');
    }else{
        WriteToHTML('output','type ' + searchType + ' keyword '+ searchKeyword + ' latestMarker '+latestMarker.coords);
        GetGooglePlaceNearbySearchResultsJSONURL(latestMarker.coords,500,searchType,searchKeyword,null);
    }
    initializePlaces();
}

function GetGooglePlaceNearbySearchResultsJSONURL(uncleanedMarkerCoords,searchRadius,searchType,searchKeyword,next_page_token){
    var url;
    var latestMarkerCoords=CleanUpLongLatString(uncleanedMarkerCoords);
    if(next_page_token==null){
        url="https://maps.googleapis.com/maps/api/place/nearbysearch/json?location="+latestMarkerCoords+"&radius="+searchRadius+"&type="+searchType+"&keyword="+searchKeyword+"&sensor=false&key="+GetAPIKey();
    }else{
        url="https://maps.googleapis.com/maps/api/place/nearbysearch/json?pagetoken="+next_page_token+"&key="+GetAPIKey();
    }
    
    WriteToHTML('output_JSONURL','<a href="'+url+'">Click here for JSON URL</a>');
}

function GetAPIKey(){
    return 'AIzaSyASDYuvialF6b8cR5HCUq6MsFuxxckw3og';
}

function GetDesiredDataFromJSON(desiredDataType, theJSONArrayToSearchFrom){
    var dataToReturn;

    if (desiredDataType == 'next_page_token'){
        for (i = 0; i < theJSONArrayToSearchFrom.results.length; i++) {
            dataToReturn[i] = theJSONArrayToSearchFrom.results[i].next_page_token;
        }
    }

    if (desiredDataType == 'name'){
        for (i = 0; i < theJSONArrayToSearchFrom.results.length; i++) {
            dataToReturn[i] = theJSONArrayToSearchFrom.results[i].name;
        }
    }

    if (desiredDataType == 'formatted_address'){
        for (i = 0; i < theJSONArrayToSearchFrom.results.length; i++) {
            dataToReturn[i] = theJSONArrayToSearchFrom.results[i].formatted_address;
        }
    }

    if (desiredDataType == 'place_id'){
        for (i = 0; i < theJSONArrayToSearchFrom.results.length; i++) {
            dataToReturn[i] = theJSONArrayToSearchFrom.results[i].place_id;
        }
    }
    
    return dataToReturn;
}

function CleanUpLongLatString(inputLongLatObject){
    var stringToCleanup=''+inputLongLatObject;
    var returnString='';
    for (i=0;i<stringToCleanup.length;i++){
        if (stringToCleanup.charAt(i)!='(' && stringToCleanup.charAt(i)!=')' && stringToCleanup.charAt(i)!=' '){
            returnString+=stringToCleanup.charAt(i);
        }
    }
    
    return returnString;
}