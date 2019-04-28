import React from 'react';
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css';
import './glmap.css'
import bbox from '@turf/bbox';


mapboxgl.accessToken = 'pk.eyJ1IjoiZGlhc2YiLCJhIjoiY2pzbmNqd2c3MGIxZDQ0bjVpa2RsZXU1YSJ9.udvxholRALOFEV4ciCh-Lg';

class YearControl {
  constructor(callback){
    this.callbackfcn=callback;
  }
  onAdd(map){
    this.map = map;
    this.container = document.createElement('div');
    this.container.className = 'year-control';

    var x = document.createElement("SELECT");
    x.setAttribute("id", "mySelect");
    document.body.appendChild(x);

    var z = document.createElement("option");
    z.setAttribute("value", "volvocar");
    var t = document.createTextNode("Volvo");
    z.appendChild(t);
    document.getElementById("mySelect").appendChild(z);
  
    // this.container.textContent = 'My custom control';
    // this.container.onclick = this.callbackfcn;
    return(this.container);
  }
  onRemove(){
    this.container.parentNode.removeChild(this.container);
    this.map = undefined;
  }
}

let Map = class Map extends React.Component {
  constructor(props){
    super(props);
    this.state={map:undefined};
  }

  addLayer(gj, heatmap){

    if (gj.features.length===0){
      return;
    }

    let bounds=bbox(gj);
    bounds=[[bounds[0],bounds[1]],
            [bounds[2],bounds[3]]];         


    if (this.map.getLayer('points')){
      this.map.removeLayer('points');  
    }
    if (this.map.getSource('points')){
      this.map.removeSource('points');
    }
    
    this.map.addSource('points',{
      "type": "geojson",
      "data": gj,
    });
    if (heatmap===false){
      this.map.addLayer({
        "id": "points",
        "type": "symbol",
        "source": 'points',
        "layout": {
          "icon-image": "{icon}-15",
          "icon-allow-overlap": true,
          "text-field": "{title}",
          'text-allow-overlap': true,
          "text-offset": [0, 0.6],
          "text-anchor": "top"
        }});  
    }else{
      this.map.addLayer({
        "id": "points",
        "type": "heatmap",
        "source": 'points',
        "paint":{
          'heatmap-opacity' : 0.5,
          'heatmap-weight' : ["log10", ["get", "count"]]
        }

      });  

    }
    if (this.props.fit===true){
      this.map.fitBounds(bounds,{
        padding: {top: 20, bottom:20, left: 30, right: 30}
      });  
    }
    this.setState({'map':this.map});
  }

  setFill(){
  }

    
  componentDidUpdate() {
    this.setFill();
  }

  componentWillReceiveProps(props){
    if ((props.geojson!==undefined)&&
    ((this.props.heatmap!==props.heatmap)||
     (this.props.year!==props.year)||
     (this.props.cummulative!==props.cummulative)||
     (this.props.selected!==props.selected))){
      this.addLayer(props.geojson, props.heatmap);
    }
  }


  componentDidMount() {
    this.map = new mapboxgl.Map({
      container: this.mapContainer,
      style: 'mapbox://styles/mapbox/light-v9',
      // interactive: false,
      zoom: 0.6,
      maxzoom: 12
    });
    this.map.on('load', () => {
      if (this.props.geojson!==undefined){
        this.addLayer(this.props.geojson);
      }
    });


    // const yearControl = new YearControl(yearSelection);
    // this.map.addControl(yearControl);
    
    
  }

  render() {
    return (
      <div ref={el => this.mapContainer = el} 
      className={(this.props.className!==undefined)?this.props.className:"absolute top right left bottom"}/>
    );
  }
}


export default Map;
