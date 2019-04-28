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
function reprGeo(g){
  let res='';
  for (let i=0; i < g.length; i++){
      res=res+'('+g[i][0]+','+g[i][1]+')';
    if (i!==(g.length-1)){
      res = res +';';
    }
  }
  return(res);
}
function reprField(article, field){
  if (article[field]!==undefined) {
    if (((typeof(article[field]) === 'string') || (article[field] instanceof String))&& (article[field].length>0))
    {
      if (article[field][article[field].length-1]!=='.'){
        return(article[field]+'. ');
      }
    }
    return(article[field]);
  }
  return(null);
}

class CitingDetails extends Component {
  constructor(props){
    super(props);
    this.state={geojson:undefined, citingList:[], cumulative: false, fit:true, heatmap:false, year:'-1'};
  }

  updateGeoJSON(articles, selected, year, cumulative){
    let gj={type: "FeatureCollection", features:[]};

    for (let i=0;i<articles[selected].cites_this.length;i++){
      
      let citingID=articles[selected].cites_this[i];
      let citing=articles[citingID];

      if (citing.coordinates===undefined){
        console.log(citing);
        continue; //WEIRD
      }
      for (let j=0; j<citing.coordinates.length; j++){
        if ((year!=='-1')&&
        (((! cumulative)&&(year!==citing.year)) ||
        ((cumulative) && (parseInt(citing.year,10) > parseInt(year,10)))
        )){
          continue;
        }

        gj.features.push({
          type: "Feature",
          properties: {
            year: citing.year,
            count : citing.coordinates.length,
            title: citing.year,
            icon: "marker"
          },
          geometry: {
            type: "Point",
            coordinates: citing.coordinates[j]
          }
        });  
      }
    }
    return(gj);
  }

  componentWillReceiveProps(props){
    if ((props.selected!==undefined)&&(props.selected!==this.props.selected)){
      let citinglist=props.articles[props.selected].cites_this.slice().sort((a,b)=>{
        return(parseInt(props.articles[a].year,10)-parseInt(props.articles[b].year,10));
      });
      let gj=this.updateGeoJSON(props.articles, props.selected, this.state.year, this.state.cumulative);
      let years=[];
      let yearsOp=[];
      for (let i=0;i<citinglist.length;i++){
        years.push(props.articles[citinglist[i]].year);
      }
      years=Array.from(new Set(years)).sort((a,b)=>{
        return(parseInt(a,10)-parseInt(b,10));
      });

      yearsOp.push({id:'-1',name:'All'})
      for (let i=0; i< years.length; i++){
        yearsOp.push({id:years[i],name:years[i]});
      }
      this.setState({geojson:gj, citingList:citinglist, yearOptions:yearsOp});
    }
  }

  render() {
    let {articles,selected}=this.props;
    let retJSX=[];
    let header=[];
    let makeTSV = () => {
      let TSV=[];
      let fields=[];
      for (let i=0; i<this.state.citingList.length; i++){
        let current=Object.keys(articles[this.state.citingList[i]]);
        for (let j=0;j<current.length;j++){
          fields.push(current[j]);
        }
      }
      fields=Array.from(new Set(fields));
      TSV.push('id\t'+fields.join('\t')+'\n');

      for (let i=0; i<this.state.citingList.length; i++){
        let article=articles[this.state.citingList[i]];  
        let line=String(this.state.citingList[i]+'\t');
        for (let j=0;j<fields.length;j++){
          let field=fields[j];
          if (article[field]!==undefined){
            switch(field){
              case 'authors':
                line = line +reprAuthors(article.authors);
                break;
              case 'coordinates':
                line = line +reprGeo(article.coordinates);
                break;
              default:
                line = line +reprField(article,field);
            }
          }
          if (j!==(fields.length-1)){
            line = line +'\t';
          }
        }
        TSV.push(line+'\n');
      }
      return(TSV);
    };
    //https://stackoverflow.com/questions/44656610/download-a-string-as-txt-file-in-react
    let downloadTxtFile = () => {
      const element = document.createElement("a");
      const file = new Blob(makeTSV(), {type: 'text/plain'});
      element.href = URL.createObjectURL(file);
      element.download = (reprAuthors(articles[selected].authors)+reprField(articles[selected],'year')+'.tsv').replace(/\s+/g, '').replace(/\.\./g,'.');
      document.body.appendChild(element); // Required for this to work in FireFox
      element.click();
    };

    if (selected!==undefined){
      header.push(<div style={{margin:'20px', display:'flex'}}>
        <h2>Works that cite: {reprAuthors(articles[selected].authors)}{reprField(articles[selected],'year')}{reprField(articles[selected],'title')}{reprField(articles[selected],'journal')}</h2>
        {/* <div className="hfill"><button onClick={downloadTxtFile}>Export tsv file</button></div> */}
        <div className="hfill"><button onClick={downloadTxtFile}>Export tsv file</button></div>
      </div>)
    }
    if (this.state.citingList!==undefined){
      for (let i=0; i<this.state.citingList.length; i++){
        let article=articles[this.state.citingList[i]];
        let author=reprAuthors(article.authors);
        // console.log(article);
        retJSX.push(<li>
            <div style={{display:'flex',width:'100%',marginTop:0}}>{author}
              {reprField(article,'year')}
              {reprField(article,'title')}
              {reprField(article,'journal')}
              {reprField(article,'vol')}
              {reprField(article,'page')}
              <div className="hfill" style={{marginTop:0}}>
                {(article.doi!==undefined)?<p style={{marginTop:0}}><a href={'http://dx.doi.org/'+article.doi} target="_blank" rel="noopener noreferrer">DOI</a></p>:null}
              </div>
          </div>
          <div className='abstract'><p>{reprField(article,'abstract')}</p></div>
          <p style={{fontSize:'small'}}>{reprField(article,'Affiliation')}</p>
        </li>)
      }
    }
    return (
      <div className="citing">
        {((this.props.geocoded!==undefined)&&(this.props.geocoded))?<div className="map">
          <Map
            geojson={this.state.geojson}
            selected={selected}
            heatmap={this.state.heatmap}
            year={this.state.year}
            fit={this.state.fit}
            cumulative={this.state.cumulative}
          />
        </div>:null}

        <div className={(this.props.geocoded)?'citationlist':'citationlistExtended'}>
          {((this.state.yearOptions!==undefined)&&(this.props.geocoded))?
          <div style={{display:'flex'}}>  
            <input 
              name="fitmap" 
              type="checkbox"              
              defaultChecked={this.state.fit}
              key={'fit'}
              onChange={(e)=>{
                this.setState({fit: e.target.checked})}} 
            /> Fit to markers
            <input 
              name="heatmap" 
              type="checkbox"              
              defaultChecked={this.state.heatmap}
              key={'heat'}
              onChange={(e)=>{
                this.setState({heatmap: e.target.checked})}} 
            /> Heatmap            
              <select 
                defaultValue={this.state.year}
                style={{marginLeft:'20px'}}
                onChange={(e)=>{
                    let selYear=e.target.value;
                    let gj=this.updateGeoJSON(this.props.articles, this.props.selected, selYear, this.state.cumulative);
                    this.setState({geojson:gj, year:selYear});
                }} >
                {this.state.yearOptions.map( (e) => {
                    return(<option 
                            value={e.id} 
                            key={e.id} 
                            
                            > 
                                {e.name}  
                          </option>)
                })}
              </select> 
            <input 
              name="cumulative" 
              type="checkbox"              
              defaultChecked={this.state.cumulative}
              key={'cumulative'}
              onChange={(e)=>{
                let gj=this.updateGeoJSON(this.props.articles, this.props.selected, this.state.year, e.target.checked);
                this.setState({geojson:gj, cumulative: e.target.checked});
              }}
            /> Cumulative
          </div>:null}
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