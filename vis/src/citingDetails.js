import React, { Component } from 'react';
import './citingDetails.css';
import Map from './glmap';
import { XYPlot, VerticalBarSeries, XAxis, YAxis, LineSeries } from 'react-vis/dist';
import verticalBarSeries from 'react-vis/dist/plot/series/vertical-bar-series';

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
function reprCiteYear(c){
  let res='';
  let keys = Object.keys(c);
  for (let i=0; i< keys.length; i++){
    res=res+'('+keys[i]+','+c[keys[i]]+')';
    if (i!==(keys.length-1)){
      res = res +';';
    }
  }
  return(res);
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

      if ((citing.coordinates===undefined)||(citing.coordinates.length===0)){
        continue; 
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
    let {articles,selected,cites_year}=this.props;
    let retJSX=[];
    let header=[];
    let makeTSVCitesYear = () => {
      let TSV=['year\tglobal\tselection\n',];
      let years=Object.keys(cites_year).sort();
      for (let i=0;i<years.length;i++){
        let line=years[i].toString()+'\t';
        if (cites_year.hasOwnProperty(years[i])){
          line=line+cites_year[years[i]].toString();
        }
        line=line+'\t';
        if ((selected!==undefined)&&(articles[selected].cites_year.hasOwnProperty(years[i])))        {
          line=line+articles[selected].cites_year[years[i]]
        }
        line=line+'\n';
        TSV.push(line);
      }
      return(TSV);
    };
    let makeTSVCitations = () => {
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
              case 'cites_year':
                line = line + reprCiteYear(article.cites_year);
                break
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
    let downloadTxtFileCitations = () => {
      const element = document.createElement("a");
      const file = new Blob(makeTSVCitations(), {type: 'text/plain'});
      element.href = URL.createObjectURL(file);
      element.download = (reprAuthors(articles[selected].authors)+reprField(articles[selected],'year')+'.tsv').replace(/\s+/g, '').replace(/\.\./g,'.');
      document.body.appendChild(element); // Required for this to work in FireFox
      element.click();
    };

    let downloadTxtFileCitesYear = () => {
      const element = document.createElement("a");
      const file = new Blob(makeTSVCitesYear(), {type: 'text/plain'});
      element.href = URL.createObjectURL(file);
      if (selected!==undefined){
        element.download = (reprAuthors(articles[selected].authors)
        +reprField(articles[selected],'year')+'.counts.tsv')
        .replace(/\s+/g, '').replace(/\.\./g,'.');
      }else{
        element.download = ('total.counts.tsv');
      }
      document.body.appendChild(element); // Required for this to work in FireFox
      element.click();
    };


    if (selected!==undefined){
      header.push(<div style={{margin:'20px', display:'flex'}}>
        <h2>Works that cite: {reprAuthors(articles[selected].authors)}{reprField(articles[selected],'year')}{reprField(articles[selected],'title')}{reprField(articles[selected],'journal')}</h2>
        {/* <div className="hfill"><button onClick={downloadTxtFileCitations}>Export tsv file</button></div> */}
        <div className="hfill"><button onClick={downloadTxtFileCitations}>Export tsv file</button></div>
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
    let all_cites_year;
    let max_global=0;
    if (cites_year!==undefined){
      all_cites_year=Object.keys(cites_year).map((d)=>{
        max_global=Math.max(max_global,cites_year[d])
        return({x:parseInt(d,10),y:cites_year[d]});
      });  
    }
    let selected_cites_year;
    let max_selected=0;
    if (selected!==undefined){
      selected_cites_year=Object.keys(articles[selected].cites_year).map((d)=>{
        max_selected=Math.max(max_selected,articles[selected].cites_year[d]);
        return({x:parseInt(d,10),y:articles[selected].cites_year[d]});
      });  
    }
    return (
      <div className="citing">
        <div className="map">
          <Map
            geojson={this.state.geojson}
            selected={selected}
            heatmap={this.state.heatmap}
            year={this.state.year}
            fit={this.state.fit}
            cumulative={this.state.cumulative}
          />
        </div>
        <div style={{display: 'flex', height: 'fit-content', width: 'fit-content'}}>
            {(this.state.yearOptions!==undefined)?
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
          </div>
        <div style={{border:'solid', borderWidth:'thin', borderColor:'lightgray'}}>
          <XYPlot
            width={790}
            height={400}
            margin={{left:50,right:60,top:20,bottom:60}}
          >
            {(selected!==undefined)?
              <VerticalBarSeries
                color={'green'}
                data={selected_cites_year.map((d)=>{
                  return({x:d.x,y:max_global*(d.y/max_selected)})
                })}
              />:null}
              {(cites_year!==undefined)?
                <VerticalBarSeries
                  data={all_cites_year}
                  color={'blue'}
                />:null}
            <XAxis
              tickLabelAngle={-30} 
              style={{
                text: {fontSize:'10px'}
              }}                  
            />
            <YAxis        
              style={{
                        line: {stroke:'blue'},
                        text: {fontSize:'10px'}
                    }}                  
            />
            {(selected!==undefined)?<YAxis        
              orientation={'right'}
              tickFormat={v => `${Math.round(max_selected*(v/max_global))}`}                            
              style={{  line: {stroke:'green'},
                        text: {fontSize:'10px'}
                    }}                  
            />:null}
          </XYPlot>
          <div style={{display:'flex'}}>
            <div style={{display:'flex', float:'left', margin: '5px'}}>
              <div style={{margin:'auto 10px', width:'10px',height:'10px',backgroundColor:'blue'}}></div>
              <p style={{margin: 'auto 0px'}}>Number of citations (total)    </p>
            </div>
            <div style={{display:'flex', float:'left', margin: '5px'}}>
              <div style={{margin:'auto 10px', width:'10px',height:'10px',backgroundColor:'green'}}></div>
              <p style={{margin: 'auto 0px'}}>Number of citations (selection)</p>
            </div>        
            <div style={{float:'right', margin:'5px'}}>
              <button
                onClick={downloadTxtFileCitesYear}
              >
                Export table
              </button>
            </div>      
          </div>
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