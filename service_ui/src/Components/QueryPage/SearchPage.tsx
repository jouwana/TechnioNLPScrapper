import React from 'react';
import { SearchComponent } from './Components/searchComponent';
import axios, {AxiosResponse} from 'axios';

export interface searchPageProps {
    keywords: string[];
    setKeywords: React.Dispatch<React.SetStateAction<string[]>>;
    setPageNumber: React.Dispatch<React.SetStateAction<number>>;
    setAxiosPromise: React.Dispatch<Promise<AxiosResponse<any, any>>>;
}

export const SearchPage: React.FC<searchPageProps> = ({keywords, setKeywords, setPageNumber, setAxiosPromise}) => {

    return (
        <>
        <button className='FAQs' onClick={()=>{setPageNumber(2); console.log("XXDDSS")}}>FAQs</button>
        <button className='run-query-button' onClick={async ()=>{
          setPageNumber(1);
          const query_body={"Query1": keywords[0]};
          const reactServer='https://technionlp-fe-service.onrender.com'
                try
                {
                    setAxiosPromise(axios.post(reactServer+'/query',query_body));              
                }
                catch (err) {
                    console.log(err);
                }                   
          }}>Run</button>
          <div className="App">
              <SearchComponent keywords={keywords} setKeywords={setKeywords} idx={0} />
              <button className='advanced-search-button' onClick={()=>{setPageNumber(3)}}>Advanced Search Options</button>
          </div>
        </>
      );
}