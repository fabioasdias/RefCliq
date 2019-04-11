import React, { Component } from 'react';
import './clusters.css';

function combineKeywords(articles, nodelist, field, numberKeywords){
    if (nodelist.length===0){
        return([]);
    }
    if (nodelist.length===1){
        return(articles[nodelist[0]][field]);
    }
    let res_dict={};
    let res=[];
    let useful=0;
    for (let i=0; i < nodelist.length; i++){
        if (articles[nodelist[i]].hasOwnProperty(field)){
            useful+=1;
            for (let j=0; j < articles[nodelist[i]][field].length; j++){
                let w=articles[nodelist[i]][field][j][0];
                let s=articles[nodelist[i]][field][j][1]
                if (res_dict.hasOwnProperty(w)){
                    res_dict[w]=res_dict[w]+s;
                }else{
                    res_dict[w]=s
                }        
            }
        }
    }
    let words = Object.keys(res_dict);
    for (let i=0; i < words.length; i++){
        res.push([words[i],res_dict[words[i]]/useful]);
    }
    res=res.sort((a,b)=>{
        return(b[1]-a[1]);
    }).slice(0,numberKeywords);    
    return(res);
}
class Clusters extends Component {
    constructor(props){
        super(props);
        this.state={extended:{},
                    min_cited:1,
                    min_articles:1}
    }
    componentWillReceiveProps(props){
        let {articles}=props;
        if (articles!==undefined){
            let maxCites=0;
            for (let a in articles){
                maxCites=Math.max(maxCites, articles[a].cites_this.length);
            }
            if (maxCites!==this.state.maxCites){
                this.setState({maxCites:maxCites});
            }
        }
    }

    render() {
        let {articles,clusters,numberKeywords}=this.props;
        let retJSX=[];
        let maxArticles=undefined;

        let prepKeywords=(keywords)=>{
            return(keywords.slice(0,numberKeywords).map((k, numberKeywords)=>{
                return(k[0]+', ');
            }));
        }
        if ((articles!==undefined) || (clusters!==undefined)){
            let nodesToUse={};
            maxArticles=0;

            for (let clusterID in clusters){
                //filter the works before doing anything else
                let nodes=clusters[clusterID].filter((d)=>{
                    return(articles[d].cites_this.length>=this.state.min_cited);
                }).sort((a,b)=>{
                    return(parseFloat(articles[b].centrality)-parseFloat(articles[a].centrality));
                });
                nodesToUse[clusterID]=nodes;
                maxArticles=Math.max(maxArticles,nodes.length);
            }

            if (this.state.min_articles>maxArticles){
                this.setState({min_articles:maxArticles});
            }

            let clusterOrder = Object.keys(clusters).sort((a,b)=>{
                return(nodesToUse[b].length-nodesToUse[a].length);
            });

            for (let cnumber=0; cnumber < clusterOrder.length; cnumber++){
                let clusterID=clusterOrder[cnumber];
                let nodes=nodesToUse[clusterID];
                if (nodes.length < this.state.min_articles){
                    continue
                }

                let keywords=combineKeywords(articles, nodes, 'keywords', numberKeywords);
                let kJSX=[];
                if (keywords.length>0){
                    kJSX.push(<p><b>Content keywords:</b> {prepKeywords(keywords)}</p>);
                }

                let cJSX=[];
                let citingKeywords=combineKeywords(articles, nodes, 'citing-keywords', numberKeywords);
                                
                if (citingKeywords.length>0){
                    cJSX.push(<p><b>Keywords of citing papers:</b> {prepKeywords(keywords)}</p>);
                }

                let works=[];
                let wrapCallBack=(e)=>{                    
                    let nodeID=e.target.getAttribute('data-node');
                    if (this.props.selectCallback !== undefined){
                        this.props.selectCallback(nodeID);
                    }
                }
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

                        works.push(<tr><td><p
                                                data-node={nodes[i]}
                                                onClick={wrapCallBack}
                                            >
                                            <a 
                                                href='#'
                                                data-node={nodes[i]}
                                                onClick={wrapCallBack}
                                                >
                                                {reference}
                                                </a>
                                            </p>
                                        </td>
                                    <td align="center">{Math.round(thisArticle.centrality*100)/100}</td>
                                    <td align="center">{thisArticle.cites_this.length}</td> 
                                    <td>{(thisArticle.keywords!==undefined)?
                                        prepKeywords(thisArticle.keywords, numberKeywords):null}</td>
                                    <td>{(thisArticle['citing-keywords']!==undefined)?
                                        prepKeywords(thisArticle['citing-keywords'], numberKeywords):null}
                                    </td></tr>
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
                                            <td><b>#Cited</b></td> 
                                            <td><b>Keywords</b></td>
                                            <td><b>Keywords of citing works</b></td></tr>
                                            {works}
                                        </tbody>
                                    </table>
                                </ul>:null}            
                            </div>);
            }
        }
      return (
        <div className="clusters">
            {(this.state.maxCites!==undefined)?
                <div style={{margin:'auto', padding:'5px', display:'flex', width:'fit-content'}}>
                    <p style={{marginRight:'20px'}}>Minimum number of citations: {this.state.min_cited} </p>
                    <p style={{marginRight:'20px'}}>1</p><input 
                        type="range" 
                        className="slider" 
                        min={1} 
                        max={this.state.maxCites} 
                        defaultValue={this.state.min_cited} 
                        onChange={(e)=>{
                            this.setState({min_cited:parseInt(e.target.value)});
                        }}
                    /><p>{this.state.maxCites}</p>
                </div>
                :null}
                {(maxArticles!==undefined)?
                <div style={{margin:'auto', padding:'5px', display:'flex', width:'fit-content'}}>
                    <p style={{marginRight:'20px'}}>Minimum number of articles in the cluster: {this.state.min_articles} </p>
                    <p style={{marginRight:'20px'}}>1</p><input 
                        type="range" 
                        className="slider" 
                        min={1} 
                        max={maxArticles} 
                        defaultValue={this.state.min_articles} 
                        onChange={(e)=>{
                            this.setState({min_articles:parseInt(e.target.value)});
                        }}
                    /><p>{maxArticles}</p>
                </div>
                :null}

            {retJSX}
        </div>
      );
    }
  }
  
  export default Clusters;
  