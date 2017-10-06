var mainArray=[];


function initMap(){
    // Map options
    var options = {
      zoom:8,
      center:{lat:42.3601,lng:-71.0589}
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

function AddToMainArray(itemToAdd){
    mainArray.push(itemToAdd);
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