import React from 'react';
import mapboxgl from 'mapbox-gl'
import 'mapbox-gl/dist/mapbox-gl.css';
import './glmap.css'
// import bbox from '@turf/bbox';


mapboxgl.accessToken = 'pk.eyJ1IjoiZGlhc2YiLCJhIjoiY2pzbmNqd2c3MGIxZDQ0bjVpa2RsZXU1YSJ9.udvxholRALOFEV4ciCh-Lg';


let Map = class Map extends React.Component {

  addLayer(gj){
    // let bounds=bbox(this.props.geojson);
    // bounds=[[bounds[0],bounds[1]],
    //         [bounds[2],bounds[3]]];         


    if (this.map.getLayer('points')){
      this.map.removeLayer('points');  
    }
    if (this.map.getSource('points')){
      this.map.removeSource('points');
    }
    
    this.map.addSource('points',{
      "type": "geojson",
      "data": gj
    });

    this.map.addLayer({
      "id": "points",
      "type": "symbol",
      "source": 'points',
      "layout": {
        "icon-image": "{icon}-15",
        "text-field": "{title}",
        "text-offset": [0, 0.6],
        "text-anchor": "top"
      }});

    // this.map.fitBounds(bounds,{
    //   padding: {top: 20, bottom:20, left: 30, right: 30}
    // });
    this.setState({'map':this.map});
    // console.log(this.map.getZoom());
  }

  setFill(){
  }

  constructor(props){
    super(props);
    this.state={map:undefined,selected:undefined,geojson:undefined}
  }
    
  componentDidUpdate() {
    this.setFill();
  }

  componentWillReceiveProps(props){
    if (this.props.selected!==props.selected){
      this.addLayer(props.geojson);
    }
  }


  componentDidMount() {
    this.map = new mapboxgl.Map({
      container: this.mapContainer,
      style: 'mapbox://styles/mapbox/light-v9',
      interactive: false,
      zoom: 0.6,
    });
    this.map.on('load', () => {
      this.addLayer(this.props.geojson);
      // console.log(this.props.geojson);
    });

    
  }

  render() {
    return (
      <div ref={el => this.mapContainer = el} 
      className={(this.props.className!==undefined)?this.props.className:"absolute top right left bottom"}/>
    );
  }
}


export default Map;
