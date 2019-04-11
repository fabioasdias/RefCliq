import React, { Component } from 'react';
import './citingDetails.css';
import Map from './glmap';

class CitingDetails extends Component {
  constructor(props){
    super(props);
    this.state={geojson:undefined, citingList:[]};
  }

  componentWillReceiveProps(props){
    if ((props.selected!==undefined)&&(props.selected!==this.props.selected)){
      let gj={type: "FeatureCollection", features:[]};
      let {articles,selected}=props;
      this.setState({citingList:articles[selected].cites_this.slice()});
      for (let i=0;i<articles[selected].cites_this.length;i++){
        let citingID=articles[selected].cites_this[i];
        let citing=articles[citingID];
        for (let j=0; j<citing.accurate_coords.length; j++){
          gj.features.push({
            type: "Feature",
            properties: {
              year: citing.year,
              "title": citing.year,
              "icon": "marker"
            },
            geometry: {
              type: "Point",
              coordinates: [citing.accurate_coords[j][0], citing.accurate_coords[j][1]]
            }
          });  
        }
      }
      this.setState({geojson:gj});
    }
  }

  render() {
    let {articles,selected}=this.props;
    let retJSX=[];
    if (this.state.citingList!==undefined){
      for (let i=0; i<this.state.citingList.length; i++){
        let article=articles[this.state.citingList[i]];
        console.log(article);

        let author='';
        for (let j=0; j<article.authors.length; j++){
          author=author+article.authors[j].last+', '+article.authors[j].first;
          if (j!==(article.authors.length-1)){
            author=author+'; ';
          }else{
            author=author+'. ';
          }

        }
        // console.log(article);
        retJSX.push(<li>
          <p>{author}
            {(article.year!==undefined)?article.year+'. ':null}
            <i>{(article.title!==undefined)?article.title+'. ':null}</i>
            {(article.journal!==undefined)?article.journal+'. ':null}
            {(article.vol!==undefined)?article.vol+'. ':null}
            {(article.page!==undefined)?article.page+'. ':null}
          </p>
          <div className='abstract'><p>{(article.abstract!==undefined)?article.abstract:null}</p></div>
          <p style={{fontSize:'small'}}>{(article.Affiliation!==undefined)?article.Affiliation.slice(1,article.Affiliation.length-1):null}</p>
        </li>)
      }
    }
    return (
      <div className="citing">
        {(this.state.geojson!==undefined)?
          <Map
            geojson={this.state.geojson}
            selected={selected}
          />
          :null}
        <div>
          <ul>
            {retJSX}
          </ul>
        </div>
      </div>
    );
  }
}
export default CitingDetails;