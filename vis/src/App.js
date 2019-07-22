import React, { Component } from 'react';
import './App.css';
import ClusterOverview from './clusterOverview';
import Clusters from './clusters';
import CitingDetails from './citingDetails';

function getData(url,actionThen){
  fetch(url)
    .then((response) => {
      if (response.status >= 400) {throw new Error("Bad response from server");}
      return response.json();
    })
    .then(actionThen);
}

class App extends Component {
  constructor(props){
    super(props);
    this.state = {nKeywords:5}
  }
  componentDidMount(){
    getData('data.json',(json)=> {
      console.log(json);
      this.setState({articles : json.articles, 
                     clusters : json.partitions,
                     graphs : json.graphs,
                     cites_year : json.cites_year,
                    });
    });
  }
  render() {
    return (
      <div className="App">
        {/* <ClusterOverview/> */}
        <div className='bottom'>
          <Clusters
            articles={this.state.articles}
            clusters={this.state.clusters}
            numberKeywords={this.state.nKeywords}
            graphs={this.state.graphs}
            selectCallback={(d)=>{
              this.setState({selected:d});
            }}
          />
          <CitingDetails
            articles={this.state.articles}
            selected={this.state.selected}
            cites_year={this.state.cites_year}
          />
        </div>
      </div>
    );
  }
}

export default App;
