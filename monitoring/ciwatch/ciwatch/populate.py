# Copyright (c) 2015 Tintri. All rights reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from ciwatch import db
from ciwatch.events import parse_json_event, add_event_to_db


def get_data():
    data = []
    with open('/var/data/third-party-ci.log') as file_:
        for line in file_:
            event = parse_json_event(line)
            if event is not None:
                data.append(event)
    return data


def load_data():
    data = get_data()
    for event in data:
        add_event_to_db(event, commit_=False)
    db.session.commit()


def main():
    db.create_projects()
    load_data()


if __name__ == '__main__':
    main()
