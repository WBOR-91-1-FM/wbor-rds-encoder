# wbor-rds-encoder

## Overview

Responsible for dynamically updating the RDS (Radio Data System) [RT (RadioText)](https://pira.cz/rds/show.asp?art=rds_encoder_support) displayed on car radios and other receivers. It takes in "Now Playing" track information and processes it before transmitting to the station's [DEVA SmartGen Mini RDS encoder](https://devabroadcast.com/smartgen-mini).

*What is RDS, you ask? Read [this primer](https://pira.cz/rds/show.asp?art=rds_encoder_support).*

**NOTE: this app is likely not suitable for transmitter networks (stations who broadcast from more than one location).** [UECP](https://www.rds.org.uk/2010/UECP.htm) is better designed for this, but not implemented in this app due to our station's single-transmitter need. From preliminary research, there are no features we "lose out on" (in our use case) by choosing to use the SmartGen's ASCII communicational protocol. This is compounded by the fact that little to no reputable/battle-tested UECP libraries exist.

## Features

- **RabbitMQ Consumer**: Consumes messages containing the currently playing track information from [Spinitron](https://spinitron.com/).
- **RDS Text Processing & Filtering**:
  - Normalize text as ASCII
  - Handles special characters by replacing or omitting them
  - Removes profane words to ensure appropriate broadcast content
- **[RT+ (RadioText Plus)](https://tech.ebu.ch/docs/techreview/trev_307-radiotext.pdf) Support**: Allows certain receivers to parse metadata fields from the RT field, such as artist and song name.
- **DEVA SmartGen Mini Integration**:
  - Maintains connection with the SmartGen RDS encoder.
  - Sends processed messages following [SmartGen ASCII Programming Syntax constraints](https://www.devabroadcast.com/dld.php?r=202) (page 34).
- **Parallel RDS Preview Publishing**:
  - Publishes processed text to a RabbitMQ exchange for consumption by a downstream preview module. For example, a web page or LED sign (e.g. BetaBrite) that reflects what is currently being shown by the RDS encoder.
  
## Message Formatting

### SmartGen ASCII Syntax Rules (in brief)

- Messages use only all-caps (capital letter) ASCII characters. The SmartGen Mini ignores ASCII inputs that do not conform to proper formatting rules.
  - Though the encoder will accept lowercase letters and all ASCII punctuation in the DPS and TEXT fields, RDS radio displays have limited character sets and may show ambiguous lowercase characters or gibberish. To assure readability, avoid fancy punctuation.
- Messages follow the format:

  ```txt
  {COMMAND}={VALUE}
  ```

  - The two commands we care about during regular operation of this app are `TEXT` AND `RT+TAG`.

- The final response line from SmartGen will return:
  - `YES` if the command was successful.
  - `NO` if it failed.
- **Character limit:** 64 characters for `TEXT=` messages.

## RT+ Configuration

To enable RT+ (RadioText Plus) for enhanced metadata parsing from FM receivers, configure the SmartGen Mini with the following:

1. **Set Group Sequence**
   - Enter the console and execute:

     ```txt
     SQC=0A,2A,3A,11A
     ```

   - This ensures the required RT+ signaling groups (11A and 3A) are active.
   - Information on what each of these represent is available in [this blog post](https://www.radioworld.com/news-and-business/lets-demystify-rds-radio-text-plus).

2. **Assign RT+ Data Group**
   - Set Group 11A as the RT+ data group:

     ```txt
     RT+GROUP=11A
     ```

## Architecture

- **Data Flow**:
  1. Spinitron sends track metadata to an [API relay](https://github.com/aidansmth/API-Relay/tree/main)
  2. An API watchdog script sees that a new track is playing and publishes the data to a RabbitMQ exchange
  3. This app consumes the RabbitMQ message, processes and sanitizes the text.
  4. The text and RT+ tags are sent to the SmartGen.
  5. (Optional) The text is published to a RabbitMQ exchange for downstream RDS previewing.

## Notes on the SmartGen Mini

By default, the SmartGen Mini encoder listens on ports `1024` and `1025`. These serve different purposes: one is designated for updating device configurations, while the other handles data traffic.

It's up to you to decide which port will be used for which function. Once you make this decision, **document it**—this will help prevent future headaches. Keep in mind that once a connection is established on a specific port, any additional connection attempts on the same port will be blocked.

For example, if this app is configured to send data to port `1024`, any attempt to connect to the encoder on this port while the app is running will fail, as the app maintains a continuous connection. To make changes to the encoder settings while the app is active, use the unoccupied port (in this case `1025`).

## TODO

- [ ] Decide on the fields coming from Spinitron
- [ ] Non-ASCII character replacement library? Or just omit sending title all together?
  - [ ] <https://stackoverflow.com/questions/3194516/replace-special-characters-with-ascii-equivalent>
  - [ ] <https://www.dcode.fr/special-characters>
  - [ ] <https://docs.asciidoctor.org/asciidoc/latest/subs/replacements/>
  - [ ] <https://github.com/zacanger/profane-words>
- [ ] Check: if disallowed characters: `$`, `^`, `` ` `` (backtick).

## Notes

- Each RT+ packed only supports two codes/tags
  - For example: `Fireflies – OWL CITY – Ocean Eyes`
  - We want to tag Title, Artist and Album. Accordingly, we would need two separate ODA packets, because we have three things to tag and each ODA packet supports two RT+ tags each. So, we need to create an RT+ ODA packet for Title and Artist, and then another tag for Album and a blank (null). Because the "Item.Toggle" bit will remain constant, the receiver will cache and cumulatively collect these tags as we interleave the transmission of these ODA packets.
- [RDS RT+ Codes](https://msx.gay/radio/rtplus)
- [Another source for RDS RT+ Codes](https://pira.cz/rds/rtpclass.pdf)
- [Inspo for RT+ syntax](https://www.thimeo.com/documentation/fm_signal_settings.html)
