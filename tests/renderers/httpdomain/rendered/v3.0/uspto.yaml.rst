.. http:get:: /

   **List available data sets**

   :resjson total:
   :resjsonobj total: integer
   :resjson apis[]:
   :resjsonobj apis[]: object
   :resjson apis[].apiKey:
      To be used as a dataset parameter value
   :resjsonobj apis[].apiKey: string
   :resjson apis[].apiVersionNumber:
      To be used as a version parameter value
   :resjsonobj apis[].apiVersionNumber: string
   :resjson apis[].apiUrl:
      The URL describing the dataset's fields
   :resjsonobj apis[].apiUrl: string:uriref
   :resjson apis[].apiDocumentationUrl:
      A URL to the API console for each API
   :resjsonobj apis[].apiDocumentationUrl: string:uriref

   :statuscode 200:
      Returns a list of data sets

      .. sourcecode:: http

         HTTP/1.1 200 OK
         Content-Type: application/json

         {
           "total": 2,
           "apis": [
             {
               "apiKey": "oa_citations",
               "apiVersionNumber": "v1",
               "apiUrl": "https://developer.uspto.gov/ds-api/oa_citations/v1/fields",
               "apiDocumentationUrl": "https://developer.uspto.gov/ds-api-docs/index.html?url=https://developer.uspto.gov/ds-api/swagger/docs/oa_citations.json"
             },
             {
               "apiKey": "cancer_moonshot",
               "apiVersionNumber": "v1",
               "apiUrl": "https://developer.uspto.gov/ds-api/cancer_moonshot/v1/fields",
               "apiDocumentationUrl": "https://developer.uspto.gov/ds-api-docs/index.html?url=https://developer.uspto.gov/ds-api/swagger/docs/cancer_moonshot.json"
             }
           ]
         }

.. http:get:: /{dataset}/{version}/fields

   **Provides the general information about the API and the list of fields that can be used to query the dataset.**

   This GET API returns the list of all the searchable field names that are in the oa_citations. Please see the 'fields' attribute which returns an array of field names. Each field or a combination of fields can be searched using the syntax options shown below.

   :param dataset:
      Name of the dataset.
   :paramtype dataset: string, required
   :param version:
      Version of the dataset.
   :paramtype version: string, required

   :statuscode 200:
      The dataset API for the given version is found and it is accessible to consume.

   :statuscode 404:
      The combination of dataset name and version is not found in the system or it is not published yet to be consumed by public.

.. http:post:: /{dataset}/{version}/records

   **Provides search capability for the data set with the given search criteria.**

   This API is based on Solr/Lucense Search. The data is indexed using SOLR. This GET API returns the list of all the searchable field names that are in the Solr Index. Please see the 'fields' attribute which returns an array of field names. Each field or a combination of fields can be searched using the Solr/Lucene Syntax. Please refer https://lucene.apache.org/core/3_6_2/queryparsersyntax.html#Overview for the query syntax. List of field names that are searchable can be determined using above GET api.

   :param version:
      Version of the dataset.
   :paramtype version: string, required
   :param dataset:
      Name of the dataset. In this case, the default value is oa_citations
   :paramtype dataset: string, required
   :formparameter criteria: *(string, required)*
      Uses Lucene Query Syntax in the format of propertyName:value, propertyName:[num1 TO num2] and date range format: propertyName:[yyyyMMdd TO yyyyMMdd]. In the response please see the 'docs' element which has the list of record objects. Each record structure would consist of all the fields and their corresponding values.
   :formparameter start: *(integer)*
      Starting record number. Default value is 0.
   :formparameter rows: *(integer)*
      Specify number of rows to be returned. If you run the search with default values, in the response you will see 'numFound' attribute which will tell the number of records available in the dataset.


   :statuscode 200:
      successful operation

   :statuscode 404:
      No matching record found for the given criteria.
