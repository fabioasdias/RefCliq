import React, { Component } from 'react';
import './citingDetails.css';
import Map from './glmap';

function reprAuthors(authors){
  let author='';
  for (let j=0; j<authors.length; j++){
    author=author+authors[j].last+', '+authors[j].first;
    if (j!==(authors.length-1)){
      author=author+'; ';
    }else{
      author=author+'. ';
    }
  }
  return(author);
}
function reprField(article, field){
  if (article[field]!==undefined){
    if (article[field][article[field].length-1]!=='.'){
      return(article[field]+'. ');
    }
    else{
      return(article[field]);
    }
  }
  return(null);
}

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
        for (let j=0; j<citing.geo.length; j++){
          let kind;
          let coords;
          if (citing.geo[j].accurate!==null){
            kind='accurate';
            coords=citing.geo[j].accurate;
          }else{
            if (citing.geo[j].generic===null){
              //no viable points
              continue;
            }
            kind='generic';
            coords=citing.geo[j].generic;
          }
          gj.features.push({
            type: "Feature",
            properties: {
              year: citing.year,
              country: citing.geo[j].country,
              kind : kind,
              title: citing.year,
              icon: "marker"
            },
            geometry: {
              type: "Point",
              coordinates: coords
            }
          });  
        }
      }
      console.log(gj);
      this.setState({geojson:gj});
    }
  }

  render() {
    let {articles,selected}=this.props;
    let retJSX=[];
    let header=[];
    if (selected!==undefined){
      header.push(<div style={{margin:'20px', display:'flex'}}>
        Works that cite: {reprAuthors(articles[selected].authors)}{reprField(articles[selected],'year')}{reprField(articles[selected],'title')}{reprField(articles[selected],'journal')}
      </div>)
    }
    if (this.state.citingList!==undefined){
      for (let i=0; i<this.state.citingList.length; i++){
        let article=articles[this.state.citingList[i]];
        let author=reprAuthors(article.authors);
        // console.log(article);
        retJSX.push(<li>
          <p style={{display:'flex'}}>{author}
            {reprField(article,'year')}
            <i>{reprField(article,'tittle')}</i>
            {reprField(article,'journal')}
            {reprField(article,'vol')}
            {reprField(article,'page')}
          </p>
          <div className='abstract'><p>{reprField(article,'abstract')}</p></div>
          <p style={{fontSize:'small'}}>{reprField(article,'Affiliation')}</p>
        </li>)
      }
    }
    return (
      <div className="citing">
        <div className="map">
          <Map
            geojson={this.state.geojson}
            selected={selected}
          />
        </div>

        <div className='citationlist'>
          {header}
          <div>
            <ul>
              {retJSX}
            </ul>
          </div>
        </div>
      </div>
    );
  }
}
export default CitingDetails;