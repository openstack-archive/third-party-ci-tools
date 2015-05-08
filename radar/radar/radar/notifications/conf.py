# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo.config import cfg

CONF = cfg.CONF

NOTIFICATION_OPTS = [
    cfg.StrOpt("rabbit_exchange_name", default="radar",
               help="The name of the topic exchange which radar will "
                    "use to broadcast its events."),
    cfg.StrOpt("rabbit_event_queue_name", default="radar_events",
               help="The name of the queue that will be created for "
                    "API events."),
    cfg.StrOpt("rabbit_application_name", default="radar",
               help="The rabbit application identifier for radar's "
                    "connection."),
    cfg.StrOpt("rabbit_host", default="localhost",
               help="Host of the rabbitmq server."),
    cfg.StrOpt("rabbit_login_method", default="AMQPLAIN",
               help="The RabbitMQ login method."),
    cfg.StrOpt("rabbit_userid", default="radar",
               help="The RabbitMQ userid."),
    cfg.StrOpt("rabbit_password", default="radar",
               help="The RabbitMQ password."),
    cfg.IntOpt("rabbit_port", default=5672,
               help="The RabbitMQ broker port where a single node is used."),
    cfg.StrOpt("rabbit_virtual_host", default="/",
               help="The virtual host within which our queues and exchanges "
                    "live."),
]