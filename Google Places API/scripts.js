var mainArray=[];

//initialize map. When user clicks on map, adds marker, and add that marker coordinate to mainArray.
function initMap(){
    // Map options
    var options = {
      zoom:8,
      center:{lat:-6.932243417891073,lng:107.63031005859375} 
    }

    // New map
    var map = new google.maps.Map(document.getElementById('map'), options);

    // Listen for click on map
    google.maps.event.addListener(map, 'click', function(event){
      // Add marker
      addMarker({coords:event.latLng});
      mainArray.push({coords:event.latLng});
    });

    // Loop through markers
    for(var i = 0;i < mainArray.length;i++){
      // Add marker
      addMarker(mainArray[i]);
    }

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

function LoopThroughArray(thisArray){
    var stringToReturn = 'text ';
    for ( i=0; thisArray.length>i; i++ ){
        stringToReturn = stringToReturn + thisArray[i].coords;
    }
    return stringToReturn;
}

function PrintResult(){
    WriteToHTML('output','PrintResult() '+LoopThroughArray(mainArray));
}