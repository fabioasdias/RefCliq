import React, { Component } from 'react';
import './clusters.css';
class Clusters extends Component {
    constructor(props){
        super(props);
        this.state={extended:{},
                    threshold:0}
    }
    render() {
        let {articles,clusters,selectCallBack,numberKeywords}=this.props;
        let retJSX=[];
        let maxCount=undefined;
        if ((articles!==undefined) || (clusters!==undefined)){
            maxCount=0;
            for (let a in articles){
                // console.log(a,articles[a].cites_this.length);
                maxCount=Math.max(maxCount, articles[a].cites_this.length);
            }
            // this.setState({maxCount:maxCount});


            for (let clusterID in clusters.nodelist){
                let keywords=(clusters.clusterKeywords[clusterID]).slice(0,numberKeywords);
                let kJSX=[];
                if (keywords.length>0){
                    kJSX.push(<p><b>Content keywords:</b> {keywords.map((k)=>{
                                    return(k[0]+', ');
                                })}</p>);
                }

                let cJSX=[];
                let citingKeywords=(clusters.citingKeywords[clusterID]).slice(0,numberKeywords);
                                
                if (citingKeywords.length>0){
                    cJSX.push(<p><b>Keywords of citing papers:</b> {citingKeywords.map((k)=>{
                        return(k[0]+', ');
                    })}</p>);
                }
                let nodes=clusters.nodelist[clusterID].filter((d)=>{
                    return(articles[d].cites_this.length>this.state.threshold);
                }).sort((a,b)=>{
                    return(parseFloat(articles[b].centrality)-parseFloat(articles[a].centrality));
                });
                if (nodes.length===0){
                    continue
                }

                let works=[];
                if ( (this.state.extended.hasOwnProperty(clusterID))&&(this.state.extended[clusterID]))
                {
                    for (let i=0;i<nodes.length;i++){
                        let thisArticle=articles[nodes[i]];
                        let reference='';
                        if (thisArticle.authors.length>0){
                            reference = reference + thisArticle.authors[0].last +', '+thisArticle.authors[0].first;
                        }
                        if (thisArticle.year !==undefined){
                            reference = reference+' ('+thisArticle.year+') ';
                        }
                        if (thisArticle.title !==undefined){
                            reference = reference+' '+thisArticle.title+'.';
                        }
                        if (thisArticle.journal !==undefined){
                            reference = reference+' '+thisArticle.journal+'.';
                        }

                        works.push(<tr><td>{reference}</td>
                                    <td align="center">{Math.round(thisArticle.centrality*100)/100}</td>
                                    <td align="center">{thisArticle.cites_this.length}</td> 
                                    <td>{(thisArticle.keywords!==undefined)?
                                        thisArticle.keywords.slice(0,numberKeywords).map((k)=>{
                                            return(k[0]+', ');
                                        }):null}</td>
                                    <td>{(thisArticle['citing-keywords']!==undefined)?thisArticle['citing-keywords'].slice(0,numberKeywords).map((k)=>{
                                            return(k[0]+', ');
                                        }):null}</td></tr>
                        );
                    }
                }
                
                retJSX.push(<div className="eachCluster">
                                <div style={{display:'flex'}}>
                                    <div style={{display:'block'}}>
                                        {kJSX}                        
                                        {cJSX}
                                    </div>
                                    <div style={{marginLeft:'auto', marginRight:'0'}}>
                                        <div style={{marginLeft:'auto', marginRight:'0', display:'flex'}}>
                                            <img 
                                                src={this.state.extended[clusterID]?"chevron-top.svg":"chevron-bottom.svg"}
                                                title={this.state.extended[clusterID]?"Collapse":"Expand"}
                                                alt={this.state.extended[clusterID]?"Collapse":"Expand"}
                                                height="18" 
                                                width="18" 
                                                data-cluster={clusterID}                            
                                                onClick={(e)=>{
                                                    let cID=e.target.getAttribute('data-cluster');
                                                    let newExtended={...this.state.extended};
                                                    if (newExtended.hasOwnProperty(cID)){
                                                        newExtended[clusterID]=!newExtended[clusterID];
                                                    }else{
                                                        newExtended[clusterID]=true;
                                                    }
                                                    this.setState({extended:newExtended});
                                                }}                            
                                                style={{paddingLeft: '2px', paddingTop:'2px', verticalAlign:'middle',cursor:'pointer',marginRight:'10px',marginLeft:'auto'}}>
                                            </img>
                                        </div>
                                        <p>Number of articles: {nodes.length}</p>
                                    </div>
                                </div>
                                
                                {(works.length>0)?<ul>
                                    <table>
                                        <tbody>
                                        <tr><td><b>Name</b></td>
                                            <td><b>Centrality</b></td>
                                            <td><b>Count</b></td> 
                                            <td><b>Keywords</b></td>
                                            <td><b>Citing keywords</b></td></tr>
                                            {works}
                                        </tbody>
                                    </table>
                                </ul>:null}            
                            </div>);
            }
        }
      return (
        <div className="clusters">
            {(maxCount!==undefined)?
                <div style={{margin:'auto', padding:'5px', display:'flex', width:'fit-content'}}>
                    <p style={{marginRight:'20px'}}>Minimum number of citations: {this.state.threshold} </p>
                    <p style={{marginRight:'20px'}}>0</p><input 
                        type="range" 
                        className="slider" 
                        min={1} 
                        max={maxCount} 
                        defaultValue={this.state.threshold} 
                        onChange={(e)=>{
                            this.setState({threshold:parseInt(e.target.value)});
                        }}
                    /><p>{maxCount}</p>
                </div>
                :null}
            {retJSX}
        </div>
      );
    }
  }
  
  export default Clusters;
  