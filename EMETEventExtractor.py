from BAM import soap_query, relevance_query
from datetime import timedelta
from time import clock
import datetime
import json
import sys
import os

global log_file
global output_file

class events:

	# Initializing all class variables
    username = ""
    password = ""
    server = ""
    output_path = ""
    log_path = ""
    filter = []
    returns = []
    webreports_events = []
    debug = ""
    
    def __init__(self):
        '''
        Assigns webreports credentials and filter value to global variables for later use.
        '''
        global log_file
        global output_file
        log_path = ""
        output_path = ""

		# Try to retrieve config file as passed argument
		# If this fails, print out appropriate error
        try:
            config_file =  sys.argv[1]
            try:
                open(config_file, "r")
            except IOError:
                print "No valid config filepath found."
        except IOError:
            print "No config filepath argument found."

        # Getting credentials from config file (JSON)
        with open(config_file, "r") as data_file:
            data = json.load(data_file)
        self.username = data["Settings"][0]["username"] 
        self.password = data["Settings"][0]["password"] 
        self.server = data["Settings"][0]["webreports_server"]
        self.returns = data["Settings"][0]["returns"]
        self.log_path = data["Settings"][0]["log_path"]
        self.output_path = data["Settings"][0]["output_path"]
        self.filter = data["Settings"][1]["filters"].values()
        self.debug = data["Settings"][0]["debug"].lower()

        #Create Default to local ouput and log paths
        if (self.log_path == ""):
            local_path = os.path.dirname(os.path.abspath(__file__))
            self.log_path = os.path.join(local_path, "EMETEventExtractor-Logs.log")
        if (self.output_path == ""):
            local_path = os.path.dirname(os.path.abspath(__file__))
            self.output_path = os.path.join(local_path, "Emet-Events.csv")

        # Opening Logs
        log_file = open(self.log_path, 'a', 0)
        current_time = datetime.datetime.now()
        log_file.write("  LOG TIME: %s \n" %current_time)
        # Print to Logs if debug is on
        if (debug == "true"):
            log_file.write("DEBUG : ON")

    def get_webreports_events(self):
        '''
        Pulls recent emet events from webreports based on filter.
        '''

        # Create Emet Return and Search properties
        # Optional EMET Timeframe Settings: Emet Triggered Mitigations for (2 hours, 30 days, a year)
        log_file.write("<get_webreports_events> : <Expecting username and password to webreports> \n")
        search = "computers"

        # Create relevance query and fetch results
        log_file.write("<get_webreports_events> : <Creating query> \n")
        query = relevance_query(self.returns, self.filter, search)
        log_file.write("<get_webreports_events> : <Getting query results> \n")
        results = soap_query(self.username, self.password, self.server, query.Query)
		log_file.write("<get_webreports_events> : <Results successfully read in.> \n")
        # Save webreports_events as dictionary
        end_time = clock()
        string = "<get_webreports_events> : <Now saving into webreports_events and exiting. %s> \n" % (timedelta(seconds = end_time - start_time))
        log_file.write(string)
        self.webreports_events = self.webreports_parse(results)

        # If debug is on, write a return of the webreports results
        if (debug == "true"):
            log_file.write("<get_webreports_events> : <DEBUG> : <Writing out webreports results to \"webreports_return.txt\" in local filepath.> \n")
            webreports_results_file = open("webreports_return.txt", "w")
            for line in results:
               webreports_results_file.write(line.encode("utf-8"))
               webreports_results_file.write("\n")

    def webreports_parse(self, results):
        '''
        Takes results from a query to webreports, and holds each result in a dictionary,
        then saves them all in a list format to the returned variable "answer".
        Expects a list of results.
        ''' 
        
        log_file.write("<webreports_parse> : <Expecting results>\n")
        answer = []
        dict = {}
        
        log_file.write("<webreports_parse> : <Now parsing results> \n")
        # Begin parsing into dictionary form
        for count in range(0, len(results)):
            new_events = results[count]
            
			# Find number of Emet values by bar count, and start parsing the EMET key/values
            num_properties = new_events.count("|")
			
            # Remove leading "(" and first comma in EMET TIME value
            if (new_events.find("TIME|") != -1):
                new_events = new_events.replace(",", "", 1).replace("( ", "", 1)
            else:
                new_events = new_events.replace("( ", "", 1)
            
            # Split by bars to get EMET key/values
            new_events = new_events.split("|")
            # Remove ending ")" in last emet property
            new_events[num_properties] = new_events[num_properties].replace(" )", "", 1)

            # Note non-emet properties and the final emet property are in the final element
            # of new_events, so we must split them by commas, and save them in a temporary list. 
            # Furthermore, we must clear this incorrect element from new_events.
            temp_list = new_events[num_properties].split(",", len(self.returns)-1)
            new_events.pop(num_properties)

            # Append the non-emet values and final emet value in temp_list to new_events
            for event in temp_list: 
                new_events.append(event)
            temp_list = []

            # Remove the ending comma in emet values
            for count in range(1, num_properties): 
                new_events[count] = new_events[count].rsplit(",", 1)

            # Now we have EMET events as list of a string, lists, and another string: 
            # (Assume there are n Key/Value pairs)
            # [ Key1, [Value1, Key2], [Value2, Key3], ...[Value n-1, Key n], Value n ]
            # Normalize into a dictionary of key value pairs
            
            for count in range(0, num_properties):
                if (count == 0):
                    # First Key/Value Pair ( Key 1, [Value 1, ... ] )
                    dict[new_events[count]] = new_events[count+1][0]
                elif (count == num_properties-1 ):
                    # Last Key/Value Pair ( [ ..., Key n ], Value n ] )
                    dict[new_events[num_properties-1][1]] = new_events[num_properties]
                else:
                    # All Key/Values in the middle ( [ ..., Key ], [ Value, ...] )
                    dict[new_events[count][1]] = new_events[count+1][0]
            
            # Create dicts out of the non-Emet properties and remove spaces in front of values 
            count = 1
            for return_property in self.returns[1:]:
                dict[return_property.replace(" ","_")] = new_events[num_properties+count][1:]
                count += 1

            # Replace commas in multiple IPs with semicolons to avoid comma parsing confusion 
            if (dict["ip_addresses"].find(")") != 0):
                dict["ip_addresses"] = dict["ip_addresses"].replace(",", ";")

            # Append the dictionary to the return list (answer) and clear the dict for the next event
            answer.append(dict.copy())
            dict.clear()

		# Update log/function time before exiting
        end_time = clock()
        string = "<webreports_parse> : <Now returning answer and exiting. %s> \n" % (timedelta(seconds = end_time - start_time))
        log_file.write(string)

        self.webreports_events = answer
        return answer

    def push_events(self):
        '''
        Deduplicates and pushes events in webreports_events in key value pairs to a file.
        '''

        log_file.write("<push_events> : <Entering push_events function. Preparing to create event strings.> \n")
		
        # Get a list of string-ified key, value events
        string_of_events = []
        temp_string = ""
        for event in self.webreports_events:
			try:
				# Place time value in first position
				if "TIME" in event:
					temp_string += "TIME=%s, " % (event["TIME"])]
				# Place all other values in string
				for key in event:
					if key != "TIME":
							temp_string += "%s=%s, " % (key.encode("utf-8"), event[key].encode("utf-8"))
				temp_string +="\n"
				string_of_events.append(temp_string)
				temp_string = ""
			except:
					f.write("<push_events> : <UnicodeEncodeError: Could not encode or decode character.> \n")
					f.write("<push_events> : <Event: %r.> \n" % event)
        
        # Deduplicate and order this list of events
        string_of_events = sorted(set(string_of_events))

        log_file.write("<push_events> : <Opening file and reading in previous events.> \n")
		
        # Pull a list of events from output file
        output_file = open(self.output_path, "a")
        output_file = open(self.output_path, "r")
        locally_cached_splunk_events = []
        for line in output_file:
            locally_cached_splunk_events.append(line)
			
        # Decode cache of file events to utf-8, and sort so they can be compared with list of events
        for count in range(0, len(locally_cached_splunk_events)):
            locally_cached_splunk_events[count] = locally_cached_splunk_events[count].decode("utf-8")
		
        locally_cached_splunk_events = sorted(set(locally_cached_splunk_events))
			
        log_file.write("<push_events> : <Creating unique events and submitting into file.> \n")

        # Get unique webreports events that are not in splunk cache
        unique_events = []
        for event in string_of_events:
            if event not in locally_cached_splunk_events:
                unique_events.append(event)

        string = "<push_events> : <There are %s unique events that will be pushed to the output file.> \n" % (len(unique_events))
        log_file.write(string)

		# Open the output file
		output_file = open(self.output_path, "a", 0)

        # Push unique_events
        for event in unique_events:
            event = event.encode("utf-8")
            output_file.write(event)
        
		# Update log/function time before exiting
		end_time = clock()
        string = "<push_events> : <Exiting function. %s> \n" % (timedelta(seconds = end_time - start_time))
        log_file.write(string)     

    def clear_logs(self):
        '''
        Clears logs if they are more than 7 days old.
        '''
        # Open Log File
        log = open(self.log_path, "r")

        # Get content of Log File
        log_content = []
        for line in log:
            log_content.append(line)

        # Logs are written oldest to newest, if you hit anything newer than 7 days,
        # keep all proceeding logs
        counter = 0
        for line in log_content:
            if (line.find("  LOG TIME: ") != -1):
                # Get Log times in datetime format
                log_time = line.replace("  LOG TIME: ", "")
                log_time = datetime.datetime.strptime(log_time, "%Y-%m-%d %H:%M:%S.%f ")
                time_now = datetime.datetime.now()
                # Test if these are less than 7 days old
                difference = (time_now - log_time)
                if (difference.days < 7):
                    # If log time is less than 7 days old, stop here
                    break
            counter += 1

        # Erase file, and only write events earlier than counter
        log = open(self.log_path, "w")
        for index in range(counter, len(log_content)):
            log.write(log_content[index])

start_time = clock()
			
### USAGE ###
my_event = events()
my_event.get_webreports_events()
my_event.push_events()
my_event.clear_logs()

## FINISHING ##
end_time = clock()
my_event.log_file.write("Now exiting. Program time was: %s \n\n" % (timedelta(seconds = end_time - start_time)))