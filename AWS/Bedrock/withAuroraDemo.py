import boto3
# Create RDS boto3 client 
rds = boto3.client('rds')

# Create RDS Data Client to run queries against Aurora PostgreSQL Database
rds_data_client = boto3.client('rds-data')

# Create variable for RDS DB Cluster Identifier
db_cluster_identifier = 'bedrockDemo'

# Create variable for RDS Database Name
db_name = 'bedrockdb'

# Use RDS boto3 client to get details about pre-configured RDS Aurora PostgreSQL Database Instance
describe_db_clusters_response = rds.describe_db_clusters(
    DBClusterIdentifier=db_cluster_identifier,
    IncludeShared=False
)

# From describe_db_clusters get value for Secret ARN and Database Cluster ARN
aurora_db_secret_arn = describe_db_clusters_response['DBClusters'][0]['MasterUserSecret']['SecretArn']
db_cluster_arn = describe_db_clusters_response['DBClusters'][0]['DBClusterArn']

# Create Schema in Aurora PostgreSQL database
schema_create_response = rds_data_client.execute_statement(
    resourceArn=db_cluster_arn,
    secretArn=aurora_db_secret_arn,
    sql='CREATE SCHEMA IF NOT EXISTS test_schema',
    database=db_name
)

# Create dept_table in Aurora PostgreSQL database
schema_create_response = rds_data_client.execute_statement(
    resourceArn=db_cluster_arn,
    secretArn=aurora_db_secret_arn,
    sql='CREATE TABLE IF NOT EXISTS test_schema.dept_table(dept_id int, dept_name varchar(100), dept_group varchar(100), dept_org_code varchar(100))',
    database=db_name
)

# Create emp_table in Aurora PostgreSQL database
schema_create_response = rds_data_client.execute_statement(
    resourceArn=db_cluster_arn,
    secretArn=aurora_db_secret_arn,
    sql='CREATE TABLE IF NOT EXISTS test_schema.emp_table(emp_id int, emp_name varchar(100), dept_id int, emp_city varchar(100), emp_state varchar(100))',
    database=db_name
)

# Create learn_catalog_table in Aurora PostgreSQL database
schema_create_response = rds_data_client.execute_statement(
    resourceArn=db_cluster_arn,
    secretArn=aurora_db_secret_arn,
    sql='CREATE TABLE IF NOT EXISTS test_schema.learn_catalog_table(learn_id int, catalog_name varchar(100), course_name int, course_category varchar(100), course_level varchar(100), course_duration int)',
    database=db_name
)

# Create emp_learning_table in Aurora PostgreSQL database
schema_create_response = rds_data_client.execute_statement(
    resourceArn=db_cluster_arn,
    secretArn=aurora_db_secret_arn,
    sql='CREATE TABLE IF NOT EXISTS test_schema.emp_learning_table(emp_id int, learn_id varchar(100), assigned_date date, start_date date, end_date date, course_status varchar(100))',
    database=db_name
)


query_list = [
{'function_name': 'func_select_dept_emp', 'query': 'select dt.dept_id, dt.dept_name, dt.dept_group, et.emp_id, et.emp_name, et.emp_city, et.emp_state From test_schema.dept_table dt join test_schema.emp_table et on dt.dept_id = et.dept_id'},
{'function_name': 'func_select_dept', 'query': 'select dept_id, dept_name, dept_group, dept_org_code from test_schema.dept_table'},
{'function_name': 'func_select_emp', 'query': 'select emp_id, emp_name, dept_id, emp_city, emp_state from test_schema.emp_table'},
{'function_name': 'func_select_learn_catalog', 'query': 'select learn_id, catalog_name, course_name, course_category, course_level, course_duration from test_schema.learn_catalog_table'},
{'function_name': 'func_select_emp_learning', 'query': 'select emp_id, learn_id, assigned_date, start_date, end_date, course_status from test_schema.emp_learning_table'},
{'function_name': 'func_select_emp_emp_learning', 'query': 'select et.emp_id, et.emp_name, et.emp_city, et.emp_state, elt.learn_id, elt.assigned_date, elt.start_date, elt.end_date, elt.course_status from test_schema.emp_table et join test_schema.emp_learning_table elt on et.emp_id = elt.emp_id'},
{'function_name': 'func_select_emp_dept_learning', 'query': 'select et.emp_id, et.emp_name, et.emp_city, et.emp_state, elt.learn_id, elt.assigned_date, elt.start_date, elt.end_date, elt.course_status, dt.dept_id, dt.dept_name, dt.dept_group from test_schema.emp_table et join test_schema.emp_learning_table elt on et.emp_id = elt.emp_id join test_schema.dept_table dt on dt.dept_id = et.dept_id'},
{'function_name': 'func_select_emp_catalog_learning', 'query': 'select et.emp_id, et.emp_name, et.emp_city, et.emp_state, elt.learn_id, elt.assigned_date, elt.start_date, elt.end_date, elt.course_status, lct.catalog_name, lct.course_name from test_schema.emp_table et join test_schema.emp_learning_table elt on et.emp_id = elt.emp_id join test_schema.learn_catalog_table lct on cast(lct.learn_id as varchar) = elt.learn_id'}
]


import boto3
from botocore.config import Config

boto3_session = boto3.session.Session()
aws_region_name = boto3_session.region_name

boto3_client_config = Config(read_timeout=1000)
bedrock_client = boto3.client(
        service_name='bedrock-runtime', region_name=aws_region_name, config=boto3_client_config
    )

model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

function_ddl_list = []

for query_dict in query_list:
    input_text = f'''
                Generate Amazon Aurora Function DDL with function_name as {query_dict['function_name']} corresponding to the select query with LANGUAGE as plpgsql, only share the query without any other text or explanation:
                {query_dict['query']}
    '''
    
    message = {
        "role": "user",
        "content": [
            {
                "text": input_text
            }
        ]
    }

    messages = [message]

    bedrock_response = bedrock_client.converse(
            modelId=model_id,
            messages=messages
        )

    output_message = bedrock_response['output']['message']
    
    function_query = output_message['content'][0]['text']
    
    function_ddl_list.append(function_query)
    
    print("####################################################")
    print(f"Input Text: {input_text}")
    print(f"Bedrock Output: {output_message}")
    
# Check for functions already present in Aurora PostgreSQL database
schema_create_response = rds_data_client.execute_statement(
    resourceArn=db_cluster_arn,
    secretArn=aurora_db_secret_arn,
    sql="SELECT routine_name FROM information_schema.routines WHERE routine_type = 'FUNCTION' AND routine_schema = 'public'",
    database=db_name
)

schema_create_response

for query in function_ddl_list:

    print(query)
    try:
        function_create_response = rds_data_client.execute_statement(
            resourceArn=db_cluster_arn,
            secretArn=aurora_db_secret_arn,
            sql=query,
            database=db_name
        )
        
        print('Function Created')
    except Exception as e:
        print("The error is: ",e)
    
    print('####################################################')

# Check for functions already present in Aurora PostgreSQL database
schema_create_response = rds_data_client.execute_statement(
    resourceArn=db_cluster_arn,
    secretArn=aurora_db_secret_arn,
    sql="SELECT routine_name FROM information_schema.routines WHERE routine_type = 'FUNCTION' AND routine_schema = 'public'",
    database=db_name
)
schema_create_response
